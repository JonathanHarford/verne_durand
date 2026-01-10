#!/usr/bin/env bb

(require '[babashka.http-client :as http]
         '[cheshire.core :as json]
         '[clojure.string :as str]
         '[babashka.cli :as cli]
         '[clojure.pprint :refer [pprint]])

;; --- Configuration ---

(def config
  {:jules-key (or System/getenv "JULES_API_KEY")})

;; --- API Helpers ---

(defn jules-request [method path]
  (let [url (str "https://jules.googleapis.com/v1alpha/sessions" path)
        headers {"X-Goog-Api-Key" (:jules-key config)}
        opts {:headers headers :throw false}
        resp (try (method url opts)
                  (catch Exception e
                    {:status 500 :body (str "Connection error: " (.getMessage e))}))
        status (:status resp)
        data (try (json/parse-string (:body resp) true)
                  (catch Exception _ {:error "Invalid JSON"}))]
    (when (>= status 400)
      (println "Jules API Error:" status (or (:error data) (:body resp))))
    data))

;; --- Formatting Helpers ---

(defn format-timestamp [ts]
  (if ts
    (-> ts
        (str/replace #"T" " ")
        (str/replace #"Z$" " UTC")
        (str/replace #"\.\d+$" ""))
    "N/A"))

(defn format-repo [source]
  (if source
    (str/replace source #"^sources/github/" "")
    "N/A"))

(defn wrap-text [text width]
  (if (or (nil? text) (empty? text))
    [""]
    (let [words (str/split text #"\s+")
          lines (reduce (fn [acc word]
                          (let [current (last acc)
                                new-line (if (empty? current)
                                           word
                                           (str current " " word))]
                            (if (<= (count new-line) width)
                              (conj (vec (butlast acc)) new-line)
                              (conj acc word))))
                        [""]
                        words)]
      lines)))

(defn print-section [title]
  (println)
  (println (str "╔" (apply str (repeat (+ (count title) 2) "═")) "╗"))
  (println (str "║ " title " ║"))
  (println (str "╚" (apply str (repeat (+ (count title) 2) "═")) "╝"))
  (println))

(defn print-field [label value & {:keys [indent wrap-width] :or {indent 0 wrap-width 80}}]
  (let [padding (apply str (repeat indent " "))
        label-str (str padding label ": ")]
    (if (string? value)
      (let [first-line-width (- wrap-width (count label-str))
            lines (wrap-text value wrap-width)
            first-line (if (empty? lines) "" (first lines))
            rest-lines (rest lines)]
        (if (<= (count first-line) first-line-width)
          (println (str label-str first-line))
          (do
            (println (str padding label ":"))
            (doseq [line lines]
              (println (str padding "  " line)))))
        (doseq [line rest-lines]
          (println (str padding "  " line))))
      (println (str label-str value)))))

;; --- Report Generation ---

(defn get-session-info [session-id]
  (let [session (jules-request http/get (str "/" session-id))
        activities (jules-request http/get (str "/" session-id "/activities?pageSize=100"))]
    {:session session
     :activities (:activities activities)}))

(defn extract-messages [activities]
  (->> activities
       reverse
       (map-indexed (fn [idx act]
                      (let [user-msg (some-> act :userMessaged :userMessage)
                            agent-msg (or (-> act :agentMessaged :agentMessage)
                                          (-> act :progressUpdated :description))
                            timestamp (:createTime act)]
                        (cond
                          user-msg {:type "User" :message user-msg :time timestamp :index idx}
                          agent-msg {:type "Agent" :message agent-msg :time timestamp :index idx}
                          :else nil))))
       (filter some?)))

(defn print-session-report [session-id]
  (println)
  (println "═══════════════════════════════════════════════════════════════")
  (println (str "  JULES SESSION REPORT: " session-id))
  (println "═══════════════════════════════════════════════════════════════")

  (let [{:keys [session activities]} (get-session-info session-id)]
    (when (:error session)
      (println "\n❌ Error fetching session:" (:error session))
      (System/exit 1))

    ;; Basic Info
    (print-section "BASIC INFORMATION")
    (print-field "Session ID" (:id session))
    (print-field "State" (:state session))
    (print-field "Created" (format-timestamp (:createTime session)))
    (print-field "Updated" (format-timestamp (:updateTime session)))

    ;; Source Context Details
    (when-let [sc (:sourceContext session)]
      (print-section "SOURCE CONTEXT")
      (print-field "Repository" (format-repo (get-in session [:sourceContext :source])))
      (print-field "Starting Branch" (or (get-in session [:sourceContext :ref])
                                         (get-in session [:sourceContext :githubRepoContext :startingBranch])
                                         "N/A"))
      (when-let [commit (:commit sc)]
        (print-field "Commit SHA" commit))
      (when-let [ref (:ref sc)]
        (print-field "Git Ref" ref)))

    ;; Initial Prompt
    (when-let [prompt (get-in session [:initialPrompt])]
      (print-section "INITIAL PROMPT")
      (doseq [line (wrap-text prompt 75)]
        (println (str "  " line))))

    ;; Outputs (PR info, etc)
    (when-let [outputs (seq (:outputs session))]
      (print-section "OUTPUTS")
      (doseq [output outputs]
        (when-let [pr (:pullRequest output)]
          (print-field "Pull Request URL" (:url pr))
          (when-let [desc (:description pr)]
            (println)
            (println "  PR Description:")
            (doseq [line (wrap-text desc 73)]
              (println (str "    " line)))))))

    ;; Recent Activities Detail
    (print-section "ACTIVITIES")
    (doseq [act (reverse activities)]
      (let [act-type (-> (dissoc act :id :name :createTime :originator)
                         keys
                         first
                         name
                         (str/replace #"([A-Z])" " $1")
                         str/capitalize)
            timestamp (format-timestamp (:createTime act))]
        (println (format "  [%s] %s" timestamp act-type))
        (when-let [details (or (-> act :progressUpdated :description)
                               (-> act :agentMessaged :agentMessage)
                               (-> act :userMessaged :userMessage))]
          (let [preview (if (> (count details) 100)
                          (str (subs details 0 97) "...")
                          details)]
            (println (str "    → " (str/replace preview #"\n" " ")))))))))

;; --- CLI ---

(def cli-opts
  {:spec
   {:help {:alias :h :desc "Show help"}}})

(defn -main [& args]
  (let [parsed (cli/parse-opts args cli-opts)
        session-id (first args)]
    (if (or (:help parsed) (nil? session-id))
      (do
        (println "Usage: session_info.bb [options] <session-id>")
        (println)
        (println "Options:")
        (println "  -h, --help    Show this help message")
        (println)
        (println "Example:")
        (println "  ./session_info.bb 12345")
        (System/exit 0))
      (print-session-report session-id))))

(when (= *file* (System/getProperty "babashka.file"))
  (apply -main *command-line-args*))
