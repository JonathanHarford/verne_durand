#!/usr/bin/env bb

(require '[babashka.http-client :as http]
         '[babashka.cli :as cli]
         '[babashka.fs :as fs]
         '[cheshire.core :as json]
         '[clojure.string :as str])

;; This is supposed to babysit Jules and poke it when it dawdles.
;; But because the API is so flaky, it's not very useful.

;; --- Configuration ---

(def config
  (atom
   {:openai-key (System/getenv "OPENAI_API_KEY")
    :jules-key (System/getenv "JULES_API_KEY")
    :model      "gpt-5-nano"
    :state-file ".jules_handled_sessions"
    :plan-doc   "docs/JULES_PLAN.md"
    :interval   5
    :page-size  5
    :quiet    false
    :repo       nil
    :session    nil
    :dry-run    false}))

(def responded-messages (atom {}))
(def target-session (atom nil))

(defn maybe-print [& args]
  (when-not (:quiet @config)
    (apply print args)
    (flush)))

(defn maybe-println [& args]
  (when-not (:quiet @config)
    (apply println args)))

;; --- State Management ---

(defn get-handled-sessions []
  (if (fs/exists? (:state-file @config))
    (set (str/split-lines (slurp (:state-file @config))))
    #{}))

(defn mark-handled! [session-id]
  (if (:dry-run @config)
    (maybe-println (format "[DRY RUN] Skipping persistent logging for session: %s" session-id))
    (do
      (spit (:state-file @config) (str session-id "\n") :append true)
      (maybe-println (format "  Session %s marked as handled." session-id)))))

;; --- API Helpers ---

(defn ask-gpt5 [system-prompt user-msg]
  (try
    (let [start (System/currentTimeMillis)
          _     (maybe-print (format "  GPT-5 (%s) is thinking..." (:model @config)))
          resp  (http/post "https://api.openai.com/v1/chat/completions"
                           {:headers {"Authorization" (str "Bearer " (:openai-key @config))
                                      "Content-Type"  "application/json"}
                            :timeout 60000 ; 60 second timeout
                            :body (json/generate-string
                                   {:model    (:model @config)
                                    :messages [{:role "system" :content system-prompt}
                                               {:role "user" :content user-msg}]})})
          end   (System/currentTimeMillis)
          _     (maybe-println (format " done (%ds)" (quot (- end start) 1000)))
          body  (json/parse-string (:body resp) true)]
      (if (not= 200 (:status resp))
        (do (println "ERROR: OpenAI API returned" (:status resp) ":" (:body resp)) nil)
        (-> body :choices first :message :content)))
    (catch Exception e
      (println "\nERROR calling OpenAI API:" (.getMessage e))
      nil)))

(defn jules-request [method path & [body]]
  (let [url (str "https://jules.googleapis.com/v1alpha/sessions" path)
        mutating? (contains? #{http/post http/put http/delete} method)
        dry-run?  (:dry-run @config)
        _ (maybe-println (format "%sJules API Request: %s %s"
                                 (cond
                                   (not dry-run?) ""
                                   mutating?      "[DRY RUN: MUTATION SKIPPED] "
                                   :else          "[DRY RUN: READ ONLY] ")
                                 (condp = method http/get "GET" http/post "POST" "REQ")
                                 url))
        headers {"X-Goog-Api-Key" (:jules-key @config)}]
    (if (and mutating? dry-run?)
      (do
        (println "DRY RUN: skipping mutating request to" url)
        (println "  Body:" (json/generate-string body))
        {:status 200 :body "{}"})
      (let [opts (cond-> {:headers headers :throw false}
                   body (assoc :headers (assoc headers "Content-Type" "application/json")
                               :body (json/generate-string body)))
            resp (try (method url opts) (catch Exception e {:status 500 :body (str "Connection error: " (.getMessage e))}))
            status (:status resp)
            data (try (json/parse-string (:body resp) true) (catch Exception _ {:error "Invalid JSON"}))]
        (when (>= status 400)
          (println "Jules API Error:" status (or (:error data) (:body resp))))
        (maybe-println "Jules API Response Status:" status "Keys:" (keys data))
        data))))

(defn send-message! [session-id message]
  (jules-request http/post (str "/" session-id ":sendMessage") {:prompt message}))

(defn create-session! [source-context prompt]
  (let [data (jules-request http/post "" {:prompt prompt :sourceContext source-context})]
    (:id data)))

(defn get-sessions []
  (let [ts         @target-session
        page-size  (:page-size @config)
        data       (if ts
                     ;; Fetch specific tracked session
                     (let [s (jules-request http/get (str "/" ts))]
                       {:sessions (if (:id s) [s] [])})
                     ;; Fallback to list search
                     (jules-request http/get (str "?pageSize=" page-size)))
        ;; Sort by updateTime descending to get the truly most recent sessions first
        sessions   (if ts (:sessions data) (reverse (sort-by :updateTime (:sessions data))))
        _ (maybe-println (format "Fetched %d sessions (limited to %d)" (count sessions) page-size))]
    (->> sessions
         (map (fn [s]
                {:id     (:id s)
                 :repo   (str/replace (get-in s [:sourceContext :source]) #"^sources/github/" "")
                 :source-context (:sourceContext s)
                 :update-time (:updateTime s)
                 :status (:state s)}))
         (filter (fn [s]
                   (let [r        (:repo @config)
                         passed   (if r (str/includes? (:repo s) r) true)]
                     (maybe-println (format "Session %s [%s] State: %s -> Match: %s" (:id s) (:repo s) (:status s) passed))
                     passed))))))

(defn get-all-activities [session-id]
  (loop [all-acts []
         token nil
         page 1]
    (let [path (str "/" session-id "/activities?pageSize=100" (if token (str "&pageToken=" token) ""))
          data (jules-request http/get path)
          acts (:activities data)
          new-token (:nextPageToken data)]
      (maybe-println (format "  Fetched page %d of activities (%d items)" page (count acts)))
      (if (and new-token (< page 10)) ; limit to 1000 items (10 pages) for safety
        (recur (into all-acts acts) new-token (inc page))
        (into all-acts acts)))))

;; WORKAROUND: Jules API's :state field doesn't accurately reflect whether a session
;; is waiting for user input. A session can show :state "IN_PROGRESS" while the web UI
;; shows it as "paused" waiting for a response. We detect waiting by analyzing activities:
;; - Unapproved plan: planGenerated without a subsequent planApproved
;; - Unanswered question: agentMessaged without a subsequent userMessaged
;; Note: Activities are returned in chronological order (oldest first), so we use (last ...)
(defn session-waiting-for-input? [session-id]
  (let [activities (get-all-activities session-id)
        ;; Check for unapproved plan: planGenerated without subsequent planApproved
        plan-gens (filter :planGenerated activities)
        plan-apps (filter :planApproved activities)
        last-plan-gen (last plan-gens)
        last-plan-app (last plan-apps)
        unapproved-plan? (and last-plan-gen
                              (or (nil? last-plan-app)
                                  (> (compare (:createTime last-plan-gen)
                                              (:createTime last-plan-app)) 0)))
        ;; Check for unanswered question: agentMessaged without subsequent userMessaged
        agent-msgs (filter :agentMessaged activities)
        user-msgs (filter :userMessaged activities)
        last-agent-msg (last agent-msgs)
        last-user-msg (last user-msgs)
        unanswered-question? (and last-agent-msg
                                  (or (nil? last-user-msg)
                                      (> (compare (:createTime last-agent-msg)
                                                  (:createTime last-user-msg)) 0)))]
    (or unapproved-plan? unanswered-question?)))

(defn get-last-agent-message [session-id]
  (let [session (jules-request http/get (str "/" session-id))
        ;; 1. If it's a completed session, look at the official outputs first (e.g. PR description)
        pr-desc (some->> (:outputs session) first :pullRequest :description)
        _ (when pr-desc (maybe-println "  Using PR description from session outputs."))

        ;; 2. Fallback: search activities newest to oldest
        activities (reverse (get-all-activities session-id))]
    (or pr-desc
        (some (fn [act]
                (let [msg (or (-> act :agentMessaged :agentMessage)
                              (-> act :progressUpdated :description)
                              (-> act :progressUpdated :review :comment)
                              (-> act :progressUpdated :review :suggestedCommitMessage)
                              (-> act :planGenerated :description)
                              (-> act :planGenerated :plan :description)
                              (some-> act :sessionCompleted :output :pullRequest :description)
                              (some-> act :artifacts :pullRequest :description))]
                  (if msg
                    (do
                      (maybe-println (format "Found message in %s (Type: %s)"
                                             (:id act)
                                             (str/join "," (keys (dissoc act :id :name :createTime :originator)))))
                      msg)
                    (let [types (keys (dissoc act :id :name :createTime :originator))]
                      (when (< (count activities) 10)
                        (maybe-println (format "Skipped %s (%s)" (:id act) (str/join "," types))))
                      nil))))
              activities))))

;; --- Logic Handlers ---

(defn handle-waiting [session]
  (when-let [last-msg (get-last-agent-message (:id session))]
    (if (= (get @responded-messages (:id session)) last-msg)
      (println (format "Jules is still waiting for session %s. Skipping." (:id session)))
      (do
        (maybe-println (format "Asking %s for judgment on session %s..." (:model @config) (:id session)))
        (if-let [decision (ask-gpt5
                           (format "Respond with EXACTLY one of these:
1. 'yes' (permission to continue)
2. 'Continue working, using your best judgment based on %s' (decision needed)
3. 'STOP' (error/human help required)" (:plan-doc @config))
                           last-msg)]
          (let [trimmed (str/trim decision)]
            (if (= trimmed "STOP")
              (do (println "STOPPED.") (System/exit 0))
              (do (maybe-println "Responding:" trimmed)
                  (send-message! (:id session) trimmed)
                  (swap! responded-messages assoc (:id session) last-msg))))
          (maybe-println "  No decision from LLM. Skipping response."))))))

(defn handle-completed [session handled]
  (let [sid (:id session)]
    (if (contains? handled sid)
      (maybe-println (format "Session %s already handled." sid))
      (do
        (maybe-println (format "Checking completed session %s..." sid))
        (if-let [final-msg (get-last-agent-message sid)]
          (if-let [decision (ask-gpt5
                             (format "Analyze message. Reply ONLY:
- 'STOP' if 100%% complete.
- 'STUCK' if needs help.
- 'CONTINUE' if more work remains based on %s." (:plan-doc @config))
                             final-msg)]
            (let [upper (str/upper-case decision)]
              (cond
                (str/includes? upper "CONTINUE")
                (let [new-id (create-session! (:source-context session)
                                              (format "Continue from %s." (:plan-doc @config)))]
                  (reset! target-session new-id))
                (str/includes? upper "STUCK") (println "STUCK.")
                :else (println "COMPLETE.")))
            (maybe-println "  No decision from LLM. Skipping chain check."))
          (println "No message found."))
        (mark-handled! sid)))))

;; --- CLI and Main ---

(def cli-opts
  {:spec
   {:repo      {:alias :r :desc "Repo to filter"}
    :session   {:alias :s :desc "Session ID"}
    :plan-doc  {:alias :p :desc "Plan doc" :default (:plan-doc @config)}
    :model     {:alias :m :desc "Model" :default (:model @config)}
    :interval  {:alias :i :desc "Interval" :default (:interval @config) :coerce :long}
    :dry-run   {:alias :n :desc "Dry run" :type :boolean :default false}
    :watch     {:alias :w :desc "Watch mode" :type :boolean :default false}
    :quiet     {:alias :q :desc "Quiet mode" :type :boolean :default false}
    :help      {:alias :h :desc "Help"}}})

(defn -main [& args]
  (let [opts (cli/parse-opts args cli-opts)]
    (if (:help opts)
      (println (cli/format-opts cli-opts))
      (do
        (swap! config merge opts)
        (when-let [s (:session opts)] (reset! target-session s))
        (let [one-check (fn []
                          (let [handled (get-handled-sessions)
                                sessions (get-sessions)
                                completed-states #{"COMPLETED" "FINISHED" "DELETING"}
                                non-completed (remove #(completed-states (:status %)) sessions)
                                completed (filter #(completed-states (:status %)) sessions)
                                new-completed (remove #(contains? handled (:id %)) completed)
                                most-recent-waiting (first (filter #(session-waiting-for-input? (:id %)) non-completed))
                                most-recent-completed (first new-completed)]
                            (cond
                              most-recent-waiting (handle-waiting most-recent-waiting)
                              most-recent-completed (handle-completed most-recent-completed handled)
                              :else (maybe-println "No actionable sessions."))))]
          (if-not (:watch @config)
            (one-check)
            (loop []
              (one-check)
              (Thread/sleep (* (:interval @config) 60 1000))
              (recur))))))))

(when (= *file* (System/getProperty "babashka.file"))
  (apply -main *command-line-args*))
