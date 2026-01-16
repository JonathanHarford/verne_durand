### Jules API Session Response Example

Source: https://developers.google.com/jules/api_hl=es

This is an example of the immediate response received after creating a new session via the Jules API. It includes the session's unique identifier, title, source context, and the prompt used.

```json
{
        "name": "sessions/31415926535897932384",
        "id": "31415926535897932384",
        "title": "Boba App",
        "sourceContext": {
          "source": "sources/github/bobalover/boba",
          "githubRepoContext": {
            "startingBranch": "main"
          }
        },
        "prompt": "Create a boba app!"
      }
```

--------------------------------

### Jules API sources.list Response Body Example

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sources/list_hl=fr

An example of the JSON response body returned by a successful sources.list API call. It includes a list of 'sources' objects and a 'nextPageToken' for pagination.

```JSON
{
  "sources": [
    {
      object (Source)
    }
  ],
  "nextPageToken": string
}
```

--------------------------------

### Example Jules Agent ListActivities Response

Source: https://developers.google.com/jules/api_hl=ko

An example of the JSON response received when listing activities for a Jules agent session. This structure includes details about the activity's name, creation time, originator (agent or user), and the content of the activity, such as a generated plan or progress updates.

```json
{
  "activities": [
    {
      "name": "sessions/14550388554331055113/activities/02200cce44f746308651037e4a18caed",
      "createTime": "2025-10-03T05:43:42.801654Z",
      "originator": "agent",
      "planGenerated": {
        "plan": {
          "id": "5103d604240042cd9f59a4cb2355643a",
          "steps": [
            {
              "id": "705a61fc8ec24a98abc9296a3956fb6b",
              "title": "Setup the environment. I will install the dependencies to run the app."
            },
            {
              "id": "bb5276efad354794a4527e9ad7c0cd42",
              "title": "Modify `src/App.js`. I will replace the existing React boilerplate with a simple Boba-themed component. This will include a title and a list of boba options.",
              "index": 1
            },
            {
              "id": "377c9a1c91764dc794a618a06772e3d8",
              "title": "Modify `src/App.css`. I will update the CSS to provide a fresh, modern look for the Boba app.",
              "index": 2
            },
            {
              "id": "335802b585b449aeabb855c722cd9c40",
              "title": "Frontend Verification. I will use the `frontend_verification_instructions` tool to get instructions on how to write a Playwright script to verify the frontend application and generate a screenshot of the changes.",
              "index": 3
            },
            {
              "id": "3e4cc97c7b2448668d1ac75b8c7b7d69",
              "title": "Submit the changes. Once the app is looking good and verified, I will submit my work.",
              "index": 4
            }
          ]
        }
      },
      "id": "02200cce44f746308651037e4a18caed"
    },
    {
      "name": "sessions/14550388554331055113/activities/2918fac8bc54450a9cbda423b7688413",
      "createTime": "2025-10-03T05:43:44.954030Z",
      "originator": "user",
      "planApproved": {
        "planId": "5103d604240042cd9f59a4cb2355643a"
      },
      "id": "2918fac8bc54450a9cbda423b7688413"
    },
    {
      "name": "sessions/14550388554331055113/activities/5b3acd1b3ca2439f9cbaefaccf7f709a",
      "createTime": "2025-10-03T05:44:16.700231Z",
      "originator": "agent",
      "progressUpdated": {
        "title": "Ran bash command",
        "description": "Command: \nnpm install\nOutput: added 1326 packages, and audited 1327 packages in 25s\n\n268 packages are looking for fundingExit Code: 0"
      },
      "artifacts": [
        {
          "bashOutput": {
            "command": "\nnpm install",
            "output": "added 1326 packages, and audited 1327 packages in 25s\n\n268 packages are looking for funding"
          }
        }
      ],
      "id": "5b3acd1b3ca2439f9cbaefaccf7f709a"
    },
    {
      "name": "sessions/14550388554331055113/activities/1ad545d812614a5b84c23a33f6120063",
      "createTime": "2025-10-03T05:44:19.502115Z",
      "originator": "agent",
      "progressUpdated": {
        "title": "I have installed the dependencies using `npm install`."
      },
      "artifacts": [
        {
          "changeSet": {
            "source": "sources/github/bobalover/boba",
            "gitPatch": {
              "baseCommitId": "36ead0a4caefc451b9652ed926a15af9570f4f35"
            }
          }
        }
      ],
      "id": "1ad545d812614a5b84c23a33f6120063"
    },
    {
      "name": "sessions/14550388554331055113/activities/3a2b46329f894ebea1faf6b8fb956428",
      "createTime": "2025-10-03T05:44:29.265425Z",
      "originator": "agent",
      "progressUpdated": {
        "title": "I have replaced the boilerplate in `src/App.js` with a Boba-themed component."
      },
      "artifacts": [
        {
          "changeSet": {
            "source": "sources/github/bobalover/boba",
            "gitPatch": {
              "unidiffPatch": "",
              "baseCommitId": "36ead0a4caefc451b9652ed926a15af9570f4f35"
            }
          }
        }
      ],
      "id": "3a2b46329f894ebea1faf6b8fb956428"
    },
    {
      "name": "sessions/14550388554331055113/activities/4e8dd66f15e247e3ae5e48eeff89ef47",
      "createTime": "2025-10-03T05:44:37.721013Z",
      "originator": "agent",
      "progressUpdated": {
        "title": "I have updated the CSS in `src/App.css` to give the app a fresh, modern look."
      },
      "artifacts": [
        {
```
    }
  ]
}
```

--------------------------------

### Resource: GitHubRepoContext

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions_hl=pt-br

Specifies the context for using a GitHub repository in a session, including the branch to start from.

```APIDOC
## Resource: GitHubRepoContext

Context to use a GitHubRepo in a session.

### JSON Representation
```json
{
  "startingBranch": string
}
```

### Fields

- **`startingBranch`** (string) - Required. The name of the branch to start the session from.
```

--------------------------------

### GET /v1alpha/sources

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sources/list_hl=es

Lists sources available through the Jules API. Supports filtering, pagination, and ordering.

```APIDOC
## GET /v1alpha/sources

### Description
Lists sources available through the Jules API. Supports filtering, pagination, and ordering.

### Method
GET

### Endpoint
`https://jules.googleapis.com/v1alpha/sources`

### Parameters
#### Query Parameters
- **filter** (string) - Optional. The filter expression for listing sources, based on AIP-160. If not set, all sources will be returned. Currently only supports filtering by name, which can be used to filter by a single source or multiple sources separated by OR. Example filters: - 'name=sources/source1 OR name=sources/source2'
- **pageSize** (integer) - Optional. The number of sources to return. Must be between 1 and 100, inclusive. If unset, defaults to 30. If set to greater than 100, it will be coerced to 100.
- **pageToken** (string) - Optional. A page token, received from a previous `sources.list` call.

### Request Body
The request body must be empty.

### Response
#### Success Response (200)
- **sources** (array of Source objects) - The sources from the specified request.
- **nextPageToken** (string) - A token, which can be sent as `pageToken` to retrieve the next page. If this field is omitted, there are no subsequent pages.

#### Response Example
```json
{
  "sources": [
    {
      "object (Source)"
    }
  ],
  "nextPageToken": "string"
}
```
```

--------------------------------

### GET /sources

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sources

Lists all available sources.

```APIDOC
## GET /sources

### Description
Lists sources.

### Method
GET

### Endpoint
`/sources`
```

--------------------------------

### GET /v1alpha/{parent=sessions/*}/activities

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions.activities/list_hl=es

Lists activities for a session. The URL uses gRPC Transcoding syntax.

```APIDOC
## GET /v1alpha/{parent=sessions/*}/activities

### Description
Lists activities for a session.

### Method
GET

### Endpoint
`https://jules.googleapis.com/v1alpha/{parent=sessions/*}/activities`

### Parameters
#### Path Parameters
- **parent** (string) - Required - The parent session, which owns this collection of activities. Format: `sessions/{session}`.

#### Query Parameters
- **pageSize** (integer) - Optional - The number of activities to return. Must be between 1 and 100, inclusive. If unset, defaults to 50. If set to greater than 100, it will be coerced to 100.
- **pageToken** (string) - Optional - A page token, received from a previous `activities.list` call.

#### Request Body
The request body must be empty.

### Response
#### Success Response (200)
- **activities** (array of Activity objects) - The activities from the specified session.
- **nextPageToken** (string) - A token, which can be sent as `pageToken` to retrieve the next page. If this field is omitted, there are no subsequent pages.

#### Response Example
```json
{
  "activities": [
    {
      "object": "Activity"
    }
  ],
  "nextPageToken": "string"
}
```
```

--------------------------------

### GET /sources

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sources_hl=de

Retrieves a list of all sources.

```APIDOC
## GET /sources

### Description

Lists sources.

### Method

GET

### Endpoint

`/sources`
```

--------------------------------

### Resource: GitHubRepoContext

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions_hl=ko

Provides context for using a GitHub repository as a source in a session, including the starting branch.

```APIDOC
## GitHubRepoContext
Context to use a GitHubRepo in a session.

### JSON Representation
```json
{
  "startingBranch": string
}
```

### Fields
* `startingBranch` (string) - Required. The name of the branch to start the session from.
```

--------------------------------

### GET /v1alpha/sources

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sources/list_hl=id

Lists all available sources. This endpoint supports filtering by name and pagination using page tokens.

```APIDOC
## GET /v1alpha/sources

### Description
Lists all available sources. This endpoint supports filtering by name and pagination using page tokens.

### Method
GET

### Endpoint
https://jules.googleapis.com/v1alpha/sources

### Parameters
#### Query Parameters
- **filter** (string) - Optional. The filter expression for listing sources. Currently only supports filtering by name, which can be used to filter by a single source or multiple sources separated by OR. Example filters: - 'name=sources/source1 OR name=sources/source2'.
- **pageSize** (integer) - Optional. The number of sources to return. Must be between 1 and 100, inclusive. If unset, defaults to 30. If set to greater than 100, it will be coerced to 100.
- **pageToken** (string) - Optional. A page token, received from a previous `sources.list` call.

### Request Body
The request body must be empty.

### Response
#### Success Response (200)
- **sources** (array of Source objects) - The sources from the specified request.
- **nextPageToken** (string) - A token, which can be sent as `pageToken` to retrieve the next page. If this field is omitted, there are no subsequent pages.

#### Response Example
```json
{
  "sources": [
    {
      "name": "sources/exampleSource1"
    },
    {
      "name": "sources/exampleSource2"
    }
  ],
  "nextPageToken": "a1b2c3d4e5f6"
}
```
```

--------------------------------

### Methods: approvePlan, create, get, list, sendMessage

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions_hl=ko

These methods allow for the management and interaction with Jules API sessions.

```APIDOC
## Methods

### POST /sessions: create
Creates a new session.

#### Request Body
* `prompt` (string) - Required. The prompt to start the session with.
* `sourceContext` (object (`SourceContext`)) - Required. The source to use in this session, with additional context.
* `title` (string) - Optional. If not provided, the system will generate one.
* `requirePlanApproval` (boolean) - Optional. Input only. If true, plans the agent generates will require explicit plan approval before the agent starts working. If not set, plans will be auto-approved.
* `automationMode` (enum (`AutomationMode`)) - Optional. Input only. The automation mode of the session. If not set, the default automation mode will be used.

### GET /sessions/{session}
Retrieves a specific session by its ID.

#### Path Parameters
* `session` (string) - Required. The ID of the session to retrieve.

### GET /sessions
Lists all sessions.

### POST /sessions/{session}:approvePlan
Approves the plan for a given session.

#### Path Parameters
* `session` (string) - Required. The ID of the session whose plan needs to be approved.

### POST /sessions/{session}:sendMessage
Sends a message to a specific session.

#### Path Parameters
* `session` (string) - Required. The ID of the session to send the message to.

#### Request Body
* `message` (string) - Required. The message to send to the session.
```

--------------------------------

### GET /v1alpha/sources

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sources/list_hl=ja

Lists available sources. This endpoint allows filtering, pagination, and retrieval of source information.

```APIDOC
## GET /v1alpha/sources

### Description
Lists available sources. This endpoint allows filtering, pagination, and retrieval of source information.

### Method
GET

### Endpoint
`https://jules.googleapis.com/v1alpha/sources`

### Parameters
#### Query Parameters
- **filter** (string) - Optional. The filter expression for listing sources, based on AIP-160. If not set, all sources will be returned. Currently only supports filtering by name, which can be used to filter by a single source or multiple sources separated by OR. Example filters: - 'name=sources/source1 OR name=sources/source2'
- **pageSize** (integer) - Optional. The number of sources to return. Must be between 1 and 100, inclusive. If unset, defaults to 30. If set to greater than 100, it will be coerced to 100.
- **pageToken** (string) - Optional. A page token, received from a previous `sources.list` call.

### Request Body
The request body must be empty.

### Response
#### Success Response (200)
- **sources** (array of objects) - The sources from the specified request. Each object has the structure defined by `Source`.
- **nextPageToken** (string) - A token, which can be sent as `pageToken` to retrieve the next page. If this field is omitted, there are no subsequent pages.

#### Response Example
```json
{
  "sources": [
    {
      "name": "sources/exampleSource1",
      "displayName": "Example Source One"
    },
    {
      "name": "sources/exampleSource2",
      "displayName": "Example Source Two"
    }
  ],
  "nextPageToken": "CAEQAg=="
}
```
```

--------------------------------

### GET /v1alpha/{name=sessions/*/activities/*}

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions.activities/get_hl=zh-cn

Retrieves a single activity resource from the Jules API.

```APIDOC
## GET /v1alpha/{name=sessions/*/activities/*}

### Description
Gets a single activity.

### Method
GET

### Endpoint
`https://jules.googleapis.com/v1alpha/{name=sessions/*/activities/*}`

### Parameters
#### Path Parameters
- **name** (string) - Required. The resource name of the activity to retrieve. Format: sessions/{session}/activities/{activity}. It takes the form `sessions/{session}/activities/{activities}`.

#### Query Parameters
None

#### Request Body
The request body must be empty.

### Request Example
```json
{
  "example": "Request body is empty."
}
```

### Response
#### Success Response (200)
- **Activity** (object) - An instance of the Activity resource.

#### Response Example
```json
{
  "example": "Activity resource object (structure not provided in source text)."
}
```
```

--------------------------------

### GET /v1alpha/sources

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sources/list_hl=fr

Lists all available sources. Supports filtering by name and pagination.

```APIDOC
## GET /v1alpha/sources

### Description
Lists all available sources. Supports filtering by name and pagination.

### Method
GET

### Endpoint
`https://jules.googleapis.com/v1alpha/sources`

### Query Parameters
#### Query Parameters
- **filter** (string) - Optional. The filter expression for listing sources, based on AIP-160. If not set, all sources will be returned. Currently only supports filtering by name, which can be used to filter by a single source or multiple sources separated by OR. Example filters: - 'name=sources/source1 OR name=sources/source2'
- **pageSize** (integer) - Optional. The number of sources to return. Must be between 1 and 100, inclusive. If unset, defaults to 30. If set to greater than 100, it will be coerced to 100.
- **pageToken** (string) - Optional. A page token, received from a previous `sources.list` call.

### Request Body
The request body must be empty.

### Response
#### Success Response (200)
- **sources** (array of Source objects) - The sources from the specified request.
- **nextPageToken** (string) - A token, which can be sent as `pageToken` to retrieve the next page. If this field is omitted, there are no subsequent pages.

#### Response Example
```json
{
  "sources": [
    {
      "sourceId": "source1",
      "name": "Example Source 1"
    },
    {
      "sourceId": "source2",
      "name": "Example Source 2"
    }
  ],
  "nextPageToken": "nextPageTokenValue"
}
```
```

--------------------------------

### Resource: GitHubRepoContext

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions_hl=ja

Provides specific context for using a GitHub repository as a source in a session, including the starting branch.

```APIDOC
## Resource: GitHubRepoContext

Context to use a GitHubRepo in a session.

### JSON Representation
```json
{
  "startingBranch": string
}
```

### Fields
*   `startingBranch` (string) - Required. The name of the branch to start the session from.
```

--------------------------------

### Methods for Source Resource

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sources_hl=id

Provides details on the available methods for interacting with the Source resource, including 'get' and 'list'.

```APIDOC
## Methods for Source Resource

### `get`

Gets a single source.

### `list`

Lists sources.
```

--------------------------------

### GET /v1alpha/sources

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sources/list_hl=zh-cn

Lists all available sources. Supports filtering by name, pagination with page size and token.

```APIDOC
## GET /v1alpha/sources

### Description
Lists all available sources. Supports filtering by name, pagination with page size and token.

### Method
GET

### Endpoint
`https://jules.googleapis.com/v1alpha/sources`

### Parameters
#### Query Parameters
- **filter** (string) - Optional. The filter expression for listing sources. Currently only supports filtering by name, which can be used to filter by a single source or multiple sources separated by OR. Example filters: 'name=sources/source1 OR name=sources/source2'.
- **pageSize** (integer) - Optional. The number of sources to return. Must be between 1 and 100, inclusive. Defaults to 30. If set to greater than 100, it will be coerced to 100.
- **pageToken** (string) - Optional. A page token, received from a previous `sources.list` call.

### Request Body
The request body must be empty.

### Response
#### Success Response (200)
- **sources** (array of Source objects) - The sources from the specified request.
- **nextPageToken** (string) - A token, which can be sent as `pageToken` to retrieve the next page. If this field is omitted, there are no subsequent pages.

#### Response Example
```json
{
  "sources": [
    {
      "name": "sources/exampleSource1",
      "displayName": "Example Source 1"
    },
    {
      "name": "sources/exampleSource2",
      "displayName": "Example Source 2"
    }
  ],
  "nextPageToken": "somePageToken"
}
```
```

--------------------------------

### GET /v1alpha/{name=sessions/*/activities/*}

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions.activities/get_hl=de

Retrieves a single activity by its resource name. The endpoint uses gRPC Transcoding syntax.

```APIDOC
## GET /v1alpha/{name=sessions/*/activities/*}

### Description
Gets a single activity by its resource name.

### Method
GET

### Endpoint
`https://jules.googleapis.com/v1alpha/{name=sessions/*/activities/*}`

### Parameters
#### Path Parameters
- **name** (string) - Required - The resource name of the activity to retrieve. Format: sessions/{session}/activities/{activity}. It takes the form `sessions/{session}/activities/{activities}`.

#### Request Body
The request body must be empty.

### Response
#### Success Response (200)
If successful, the response body contains an instance of `Activity`.
```

--------------------------------

### List Activities for a Session (HTTP GET)

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions.activities/list_hl=fr

This snippet demonstrates how to list activities for a given session using an HTTP GET request to the Jules API. It requires a parent session ID and supports optional query parameters for pagination.

```HTTP
GET https://jules.googleapis.com/v1alpha/{parent=sessions/*}/activities?pageSize=100&pageToken="string"
```

--------------------------------

### HTTP GET Request for Jules API Activity

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions.activities/get_hl=de

This snippet shows the structure of an HTTP GET request to retrieve a specific activity from the Jules API. It includes the base URL and the required path parameter format. The request body is empty.

```http
GET https://jules.googleapis.com/v1alpha/{name=sessions/*/activities/*}
```

--------------------------------

### GET /v1alpha/sessions

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions/list_hl=es

Lists all available sessions. This endpoint supports pagination through `pageSize` and `pageToken` query parameters.

```APIDOC
## GET /v1alpha/sessions

### Description
Lists all sessions. This endpoint allows for retrieval of sessions with optional pagination.

### Method
GET

### Endpoint
https://jules.googleapis.com/v1alpha/sessions

### Parameters
#### Query Parameters
- **pageSize** (integer) - Optional. The number of sessions to return. Must be between 1 and 100, inclusive. If unset, defaults to 30. If set to greater than 100, it will be coerced to 100.
- **pageToken** (string) - Optional. A page token, received from a previous `sessions.list` call.

### Request Body
The request body must be empty.

### Response
#### Success Response (200)
- **sessions** (array of Session objects) - The sessions from the specified request.
- **nextPageToken** (string) - A token, which can be sent as `pageToken` to retrieve the next page. If this field is omitted, there are no subsequent pages.

#### Response Example
```json
{
  "sessions": [
    {
      "exampleSessionField": "exampleSessionValue"
    }
  ],
  "nextPageToken": "examplePageToken"
}
```
```

--------------------------------

### Resource: GitHubRepoContext

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions_hl=de

Specifies the context for using a GitHub repository within a session, including the starting branch.

```APIDOC
## Resource: GitHubRepoContext

Context to use a GitHubRepo in a session.

### JSON Representation
```json
{
  "startingBranch": string
}
```

### Fields

*   **`startingBranch`** (string) - Required. The name of the branch to start the session from.
```

--------------------------------

### GET /v1alpha/{parent=sessions/*}/activities

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions.activities/list_hl=de

Lists activities for a given session. This endpoint supports pagination.

```APIDOC
## GET /v1alpha/{parent=sessions/*}/activities

### Description
Lists activities for a session. This endpoint supports pagination.

### Method
GET

### Endpoint
`https://jules.googleapis.com/v1alpha/{parent=sessions/*}/activities`

### Parameters
#### Path Parameters
- **parent** (string) - Required - The parent session, which owns this collection of activities. Format: `sessions/{session}`.

#### Query Parameters
- **pageSize** (integer) - Optional - The number of activities to return. Must be between 1 and 100, inclusive. Defaults to 50. If set to greater than 100, it will be coerced to 100.
- **pageToken** (string) - Optional - A page token, received from a previous `activities.list` call.

#### Request Body
The request body must be empty.

### Response
#### Success Response (200)
- **activities** (array of Activity objects) - The activities from the specified session.
- **nextPageToken** (string) - A token, which can be sent as `pageToken` to retrieve the next page. If this field is omitted, there are no subsequent pages.

#### Response Example
```json
{
  "activities": [
    {
      "object": "Activity"
    }
  ],
  "nextPageToken": "string"
}
```
```

--------------------------------

### Resource: GitHubRepoContext

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions_hl=zh-cn

Provides context for using a GitHub repository in a session, specifically indicating the starting branch.

```APIDOC
## Resource: GitHubRepoContext
Context to use a GitHubRepo in a session.

### Fields
- **startingBranch** (string) - Required. The name of the branch to start the session from.
```

--------------------------------

### Sample ListActivities Response (JSON)

Source: https://developers.google.com/jules/api

This is an example of a response when listing activities in a Jules session. It contains a list of activities, each with details like name, creation time, originator, and the type of action performed (e.g., planGenerated, planApproved, progressUpdated).

```json
{
  "activities": [
    {
      "name": "sessions/14550388554331055113/activities/02200cce44f746308651037e4a18caed",
      "createTime": "2025-10-03T05:43:42.801654Z",
      "originator": "agent",
      "planGenerated": {
        "plan": {
          "id": "5103d604240042cd9f59a4cb2355643a",
          "steps": [
            {
              "id": "705a61fc8ec24a98abc9296a3956fb6b",
              "title": "Setup the environment. I will install the dependencies to run the app."
            },
            {
              "id": "bb5276efad354794a4527e9ad7c0cd42",
              "title": "Modify `src/App.js`. I will replace the existing React boilerplate with a simple Boba-themed component. This will include a title and a list of boba options.",
              "index": 1
            },
            {
              "id": "377c9a1c91764dc794a618a06772e3d8",
              "title": "Modify `src/App.css`. I will update the CSS to provide a fresh, modern look for the Boba app.",
              "index": 2
            },
            {
              "id": "335802b585b449aeabb855c722cd9c40",
              "title": "Frontend Verification. I will use the `frontend_verification_instructions` tool to get instructions on how to write a Playwright script to verify the frontend application and generate a screenshot of the changes.",
              "index": 3
            },
            {
              "id": "3e4cc97c7b2448668d1ac75b8c7b7d69",
              "title": "Submit the changes. Once the app is looking good and verified, I will submit my work.",
              "index": 4
            }
          ]
        }
      },
      "id": "02200cce44f746308651037e4a18caed"
    },
    {
      "name": "sessions/14550388554331055113/activities/2918fac8bc54450a9cbda423b7688413",
      "createTime": "2025-10-03T05:43:44.954030Z",
      "originator": "user",
      "planApproved": {
        "planId": "5103d604240042cd9f59a4cb2355643a"
      },
      "id": "2918fac8bc54450a9cbda423b7688413"
    },
    {
      "name": "sessions/14550388554331055113/activities/5b3acd1b3ca2439f9cbaefaccf7f709a",
      "createTime": "2025-10-03T05:44:16.700231Z",
      "originator": "agent",
      "progressUpdated": {
        "title": "Ran bash command",
        "description": "Command: \nnpm install\nOutput: added 1326 packages, and audited 1327 packages in 25s\n\n268 packages are looking for fundingExit Code: 0"
      },
      "artifacts": [
        {
          "bashOutput": {
            "command": "\nnpm install",
            "output": "added 1326 packages, and audited 1327 packages in 25s\n\n268 packages are looking for funding"
          }
        }
      ],
      "id": "5b3acd1b3ca2439f9cbaefaccf7f709a"
    },
    {
      "name": "sessions/14550388554331055113/activities/1ad545d812614a5b84c23a33f6120063",
      "createTime": "2025-10-03T05:44:19.502115Z",
      "originator": "agent",
      "progressUpdated": {
        "title": "I have installed the dependencies using `npm install`."
      },
      "artifacts": [
        {
          "changeSet": {
            "source": "sources/github/bobalover/boba",
            "gitPatch": {
              "baseCommitId": "36ead0a4caefc451b9652ed926a15af9570f4f35"
            }
          }
        }
      ],
      "id": "1ad545d812614a5b84c23a33f6120063"
    },
    {
      "name": "sessions/14550388554331055113/activities/3a2b46329f894ebea1faf6b8fb956428",
      "createTime": "2025-10-03T05:44:29.265425Z",
      "originator": "agent",
      "progressUpdated": {
        "title": "I have replaced the boilerplate in `src/App.js` with a Boba-themed component."
      },
      "artifacts": [
        {
          "changeSet": {
            "source": "sources/github/bobalover/boba",
            "gitPatch": {
              "unidiffPatch": "",
              "baseCommitId": "36ead0a4caefc451b9652ed926a15af9570f4f35"
            }
          }
        }
      ],
      "id": "3a2b46329f894ebea1faf6b8fb956428"
    },
    {
      "name": "sessions/14550388554331055113/activities/4e8dd66f15e247e3ae5e48eeff89ef47",
      "createTime": "2025-10-03T05:44:37.721013Z",
      "originator": "agent",
      "progressUpdated": {
        "title": "I have updated the CSS in `src/App.css` to give the app a fresh, modern look."
      },
      "artifacts": [
        {
          "changeSet": {
            "source": "sources/github/bobalover/boba",
            "gitPatch": {
              "unidiffPatch": "",
              "baseCommitId": "36ead0a4caefc451b9652ed926a15af9570f4f35"
            }
          }
        }
      ],
      "id": "4e8dd66f15e247e3ae5e48eeff89ef47"
    }
  ]
}
```

--------------------------------

### GET /v1alpha/{name=sources/**}

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sources/get_hl=zh-cn

Retrieves a single source by its resource name.

```APIDOC
## GET /v1alpha/{name=sources/**}

### Description
Gets a single source.

### Method
GET

### Endpoint
`https://jules.googleapis.com/v1alpha/{name=sources/**}`

### Parameters
#### Path Parameters
- **name** (string) - Required - The resource name of the source to retrieve. Format: sources/{source}. It takes the form `sources/{+source}`.

#### Query Parameters
None

#### Request Body
The request body must be empty.

### Request Example
```json
{
  "example": "empty request body"
}
```

### Response
#### Success Response (200)
- **Source** (object) - An instance of the Source object if successful.

#### Response Example
```json
{
  "example": "Source object"
}
```
```

--------------------------------

### Session Management Methods

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions_hl=pt-br

Provides methods for managing sessions, including approving plans, creating, getting, and listing sessions.

```APIDOC
## Session Management Methods

### `approvePlan`

#### Description
Approves a plan in a session.

### `create`

#### Description
Creates a new session.

### `get`

#### Description
Gets a single session.

### `list`

#### Description
Lists all sessions.
```

--------------------------------

### GET /sources/{source}

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sources_hl=de

Retrieves a single source by its identifier.

```APIDOC
## GET /sources/{source}

### Description

Gets a single source.

### Method

GET

### Endpoint

`/sources/{source}`

### Parameters

#### Path Parameters

*   **source** (string) - Required - The identifier of the source to retrieve.
```

--------------------------------

### Resource: GitHubRepoContext

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions_hl=es

Contains specific context for using a GitHub repository in a session, including the branch to start from.

```APIDOC
## Resource: GitHubRepoContext
Context to use a GitHubRepo in a session.

### JSON Representation
```json
{
  "startingBranch": string
}
```

### Fields
*   `startingBranch` (string) - Required. The name of the branch to start the session from.
```

--------------------------------

### Resource: GitHubRepoContext

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions_hl=ru

Provides context for using a GitHub repository within a session, specifying the starting branch.

```APIDOC
## Resource: GitHubRepoContext

Context to use a GitHubRepo in a session.

### JSON Representation
```json
{
  "startingBranch": string
}
```

### Fields

*   **`startingBranch`** (`string`) - Required. The name of the branch to start the session from.
```

--------------------------------

### GET /v1alpha/{name=sessions/*}

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions/get

Retrieves a single session resource by its name.

```APIDOC
## GET /v1alpha/{name=sessions/*}

### Description
Gets a single session.

### Method
GET

### Endpoint
`https://jules.googleapis.com/v1alpha/{name=sessions/*}`

### Parameters
#### Path Parameters
- **name** (string) - Required - The resource name of the session to retrieve. Format: `sessions/{session}`. It takes the form `sessions/{session}`.

#### Query Parameters
None

#### Request Body
The request body must be empty.

### Request Example
None (GET request with empty body)

### Response
#### Success Response (200)
- **Session** (object) - An instance of the `Session` resource.

#### Response Example
```json
{
  "name": "sessions/exampleSessionId",
  "description": "Example session details"
}
```
```

--------------------------------

### Activity API

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions

Provides methods to interact with activities, including getting a single activity and listing activities for a session.

```APIDOC
## Methods

### `get`
Gets a single activity.

### `list`
Lists activities for a session.
```

--------------------------------

### GET /v1alpha/sessions

Source: https://developers.google.com/jules/api

Lists available sessions. Useful for retrieving existing sessions and their statuses.

```APIDOC
## GET /v1alpha/sessions

### Description
Lists sessions. You can specify the maximum number of sessions to return.

### Method
GET

### Endpoint
`https://jules.googleapis.com/v1alpha/sessions`

### Parameters
#### Query Parameters
- **pageSize** (integer) - Optional - The maximum number of sessions to return. Defaults to a reasonable number if not specified.

#### Request Body
None

### Request Example
```bash
curl 'https://jules.googleapis.com/v1alpha/sessions?pageSize=5' \
    -H 'X-Goog-Api-Key: YOUR_API_KEY'
```

### Response
#### Success Response (200)
Returns a list of session objects. The structure of each session object is similar to the response of the Create Session endpoint.
```

--------------------------------

### GET /sources/{source}

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sources_hl=ko

Gets a single source by its ID.

```APIDOC
## GET /sources/{source}

### Description

Gets a single source.

### Method

GET

### Endpoint

`/sources/{source}`

### Parameters

#### Path Parameters

*   **source** (string) - Required - The ID of the source to retrieve.
```

--------------------------------

### GET /v1alpha/sessions

Source: https://developers.google.com/jules/api_hl=id

Lists sessions associated with the authenticated user. Supports pagination.

```APIDOC
## GET /v1alpha/sessions

### Description
Lists sessions associated with the authenticated user. You can specify the number of sessions to return using the `pageSize` query parameter.

### Method
GET

### Endpoint
`https://jules.googleapis.com/v1alpha/sessions`

### Parameters
#### Query Parameters
- **pageSize** (integer) - Optional - Specifies the maximum number of sessions to return.

### Response
#### Success Response (200)
- **sessions** (array) - A list of session objects.
  - Each session object contains fields like `name`, `id`, `title`, `sourceContext`, and `prompt`.

#### Response Example
```json
{
  "sessions": [
    {
      "name": "sessions/31415926535897932384",
      "id": "31415926535897932384",
      "title": "Boba App",
      "sourceContext": {
        "source": "sources/github/bobalover/boba",
        "githubRepoContext": {
          "startingBranch": "main"
        }
      },
      "prompt": "Create a boba app!"
    }
  ]
}
```
```

--------------------------------

### GET /v1alpha/sessions

Source: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions/list

Lists all available sessions. Supports pagination through `pageSize` and `pageToken` query parameters.

```APIDOC
## GET /v1alpha/sessions

### Description
Lists all available sessions. This endpoint supports pagination using `pageSize` and `pageToken` query parameters.

### Method
GET

### Endpoint
`https://jules.googleapis.com/v1alpha/sessions`

### Parameters
#### Query Parameters
- **pageSize** (integer) - Optional. The number of sessions to return. Must be between 1 and 100, inclusive. If unset, defaults to 30. If set to greater than 100, it will be coerced to 100.
- **pageToken** (string) - Optional. A page token, received from a previous `sessions.list` call.

#### Request Body
The request body must be empty.

### Response
#### Success Response (200)
- **sessions** (array of objects) - The sessions from the specified request. Each object has the structure defined by the `Session` type.
- **nextPageToken** (string) - A token, which can be sent as `pageToken` to retrieve the next page. If this field is omitted, there are no subsequent pages.

#### Response Example
```json
{
  "sessions": [
    {
      "sessionId": "exampleSession1",
      "displayName": "Example Session One"
    },
    {
      "sessionId": "exampleSession2",
      "displayName": "Example Session Two"
    }
  ],
  "nextPageToken": "CAESABJkYXRhc2V0X2lkXzEyMw=="
}
```
```

--------------------------------

### POST /v1alpha/sessions

Source: https://developers.google.com/jules/api_hl=ru

Creates a new development session. This request tells Jules to create a boba app in the specified repository. The `automationMode` field is optional.

```APIDOC
## POST /v1alpha/sessions

### Description
Creates a new development session for generating code or applications within a specified repository. The `automationMode` field is optional and controls whether a Pull Request is automatically created.

### Method
POST

### Endpoint
https://jules.googleapis.com/v1alpha/sessions

### Parameters
#### Query Parameters
- **pageSize** (integer) - Optional - The maximum number of sessions to return.

#### Request Body
- **prompt** (string) - Required - The prompt describing the desired application or code to generate.
- **sourceContext** (object) - Required - Specifies the source repository and context.
  - **source** (string) - Required - The source identifier (e.g., "sources/github/user/repo").
  - **githubRepoContext** (object) - Optional - GitHub specific repository context.
    - **startingBranch** (string) - Required - The branch to start from.
- **automationMode** (string) - Optional - The automation mode for the session (e.g., "AUTO_CREATE_PR"). Defaults to no automatic PR creation.
- **title** (string) - Required - A title for the session.
- **requirePlanApproval** (boolean) - Optional - If true, requires explicit plan approval. Defaults to false.

### Request Example
```json
{
  "prompt": "Create a boba app!",
  "sourceContext": {
    "source": "sources/github/bobalover/boba",
    "githubRepoContext": {
      "startingBranch": "main"
    }
  },
  "automationMode": "AUTO_CREATE_PR",
  "title": "Boba App"
}
```

### Response
#### Success Response (200)
- **name** (string) - The unique identifier of the created session.
- **id** (string) - The ID of the created session.
- **title** (string) - The title of the session.
- **sourceContext** (object) - The source context used for the session.
- **prompt** (string) - The prompt used for the session.
- **outputs** (array) - An array of outputs, which may include pull request details if `automationMode` was used.
  - **pullRequest** (object) - Details of the pull request.
    - **url** (string) - The URL of the pull request.
    - **title** (string) - The title of the pull request.
    - **description** (string) - The description of the pull request.

#### Response Example
```json
{
  "name": "sessions/31415926535897932384",
  "id": "31415926535897932384",
  "title": "Boba App",
  "sourceContext": {
    "source": "sources/github/bobalover/boba",
    "githubRepoContext": {
      "startingBranch": "main"
    }
  },
  "prompt": "Create a boba app!",
  "outputs": [
    {
      "pullRequest": {
        "url": "https://github.com/bobalover/boba/pull/35",
        "title": "Create a boba app",
        "description": "This change adds the initial implementation of a boba app."
      }
    }
  ]
}
```
```