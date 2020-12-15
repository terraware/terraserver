# Data Model

## High-level concepts

### The resource hierarchy

The server can store arbitrary data in a filesystem-like hierarchy of folders.
The resources files and folders are accessed by URLs in the same way that file system
objects are accessed using paths. Each resource has a type:

* organization folder: the top-level folder corresponding to an organization
* controller folder: a folder corresponding to a controller
* basic folder: a folder that can contain other resources
* file: a text or binary file (image, CSV, markdown, etc.)
* sequence: a time series of values (numeric, string, or images)

Non-folder resources (files and sequences) are represented as a time-ordered list of
resource revisions. In a sequence, these revisions are timestamped values of the time series.
A log file can be represented as a sequence of text values. In the case of files,
the revisions provide a history of previous versions of the file data or app specification.

Large resource revisions can be placed in bulk storage (e.g. S3). Small resource revisions are
placed directly in the server database.

#### Folder organization

Folders can be nested in an arbitrary hierarchy, but the top-level resource (the first element in the resource path) must always be an organization folder, and organization folders cannot appear below the top level of the hierarchy.

Typically, each controller will have its own controller folder, and each device managed by that controller will have a basic folder under the controller folder. Concretely, a typical resource path will look like:

    /organization/controller/device/sequence

For large installations, the folders can be further subdivided if needed using additional levels of basic folders.

#### Permissions

Each resource has an optional list of permissions that controls which entities have access to the resource. If a resource doesn't have permissions, it inherits the permissions of the closest ancestor that has permissions. That is, setting the permissions on a folder causes those permissions to become the default permissions for all the contents of the folder.

Permissions are additive: a resource inherits the permissions from all its ancestors unless it overrides them.

Each entry in a resource's permissions list has three parts: an access type, a principal, and an access level, all represented by numeric values.

The access type determines how the principal is interpreted, and must be one of the following.

| ID  | Name                     | Description                                 | Principal meaning
| --- | ------------------------ | ------------------------------------------- | -----------------
| 100 | Public                   | All users and controllers                   | None; principal is ignored
| 110 | Organization users       | Users who are members of an organization    | Organization folder's resource ID
| 120 | Organization controllers | Controllers associated with an organization | Organization folder's resource ID
| 130 | User                     | A specific user                             | User ID
| 140 | Controller               | A specific controller                       | Controller folder's resource ID

The access level must be one of the following.

| ID  | Description
| --- | ---
| 0   | Deny access. This is used to override permissions on parent folders.
| 10  | Read-only access.
| 20  | Read and write access.

Concretely, permissions are stored in the database as a JSON-encoded list of lists. So for example, a permission to allow read access to users in organization 1234 and write access to controllers in the same organization would look like:

```json
[[110, 10, 1234], [120, 20, 1234]]
```

## Schema

### account\_requests

Outgoing user invitations. Used to verify the access codes in links when people click on them in invitation email.

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`                 | integer   | not null |                |
| `organization_name`  | text(100) |          |                | Human-readable organization name, pulled from the `full_name` system attribute on the organization folder
| `organization_id`    | integer   |          | `resources.id` |
| `inviter_id`         | integer   |          | `users.id`     |
| `creation_timestamp` | timestamp | not null |                |
| `redeemed_timestamp` | timestamp |          |                |
| `access_code`        | text(40)  | not null |                | Randomly generated code
| `email_address`      | text      | not null |                |
| `email_sent`         | boolean   | not null |                | If true, email was successfully sent to an email server; does not indicate successful delivery to the recipient
| `email_failed`       | boolean   | not null |                | If true, all attempts to send the email failed
| `attributes`         | text      | not null |                | JSON object with additional data about the request; currently always `{}`

### action\_throttles

Used for rate limiting of actions such as email alerts. Rate limiting is per-user or per-controller.

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`            | integer  | not null |                |
| `controller_id` | integer  |          | `resources.id` |
| `user_id`       | integer  |          | `users.id`     |
| `type`          | text(50) | not null |                | See below
| `recent_usage`  | text     | not null |                | See below

One of `controller_id` or `user_id` must be present and indicates which principal is performing the action.

`type` indicates the specific action being throttled. There are no restrictions on the value other than the maximum length, but currently the server uses the following values:

* `send_email`
* `send_text_message`

`recent_usage` is a comma-delimited list of integer POSIX timestamps in ascending order representing recent occurrences of the action.

### controller\_status

Monitoring data for each controller, to allow for alerting if controllers die.

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`                         | integer   | not null | `resources.id` |
| `client_version`             | text(80)  | not null |                |
| `web_socket_connected`       | boolean   | not null |                |
| `last_connect_timestamp`     | timestamp |          |                |
| `last_watchdog_timestamp`    | timestamp |          |                | When the most recent watchdog heartbeat was received from the controller
| `watchdog_notification_sent` | boolean   | not null |                | An alert has already been generated for the current lack of a watchdog request
| `attributes`                 | text      | not null |                |

### keys

API keys used by controllers and users. **TODO: Link to docs about key-based authentication.**

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`                      | integer   | not null |                |
| `organization_id`         | integer   | not null | `resources.id` |
| `creation_user_id`        | integer   | not null | `users.id`     |
| `revocation_user_id`      | integer   |          | `users.id`     |
| `creation_timestamp`      | timestamp | not null |                |
| `revocation_timestamp`    | timestamp |          |                |
| `access_as_user_id`       | integer   |          | `users.id`     |
| `access_as_controller_id` | integer   |          | `resources.id` |
| `key_part`                | text(8)   | not null |                |
| `key_hash`                | text(128) | not null |                |
| `key_storage`             | text      |          |                |
| `key_storage_nonce`       | text      |          |                |

### messages

**Obsolete!** This was used as the queue for real-time messaging before the server switched to using MQTT.

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`                   | bigint    | not null |                |
| `timestamp`            | timestamp | not null |                |
| `sender_controller_id` | integer   |          | `resources.id` |
| `sender_user_id`       | integer   |          | `users.id`     |
| `folder_id`            | integer   | not null | `resources.id` |
| `type`                 | text(40)  | not null |                |
| `parameters`           | text      | not null |                |
| `attributes`           | text      |          |                |

### organization\_users

Associates users with organizations. A user may be a member of multiple organizations.

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`              | integer | not null |                |
| `organization_id` | integer | not null | `resources.id` |
| `user_id`         | integer | not null | `users.id`     |
| `is_admin`        | boolean | not null |                |

### outgoing\_messages

Stores the contents of outgoing email and SMS messages.

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`            | integer   | not null |                |
| `controller_id` | integer   |          | `resources.id` | Identity of sender if email was sent by a controller
| `user_id`       | integer   |          | `users.id`     | Identity of sender if email was sent by a user
| `timestamp`     | timestamp | not null |                |
| `recipients`    | text      | not null |                | Comma-delimited list of phone numbers or email addresses
| `message`       | text      | not null |                | See below
| `attributes`    | text      | not null |                | JSON object with additional attributes; currently always `{}`

`message` is the content of the text message for an outgoing SMS, and is the _subject line_ of an outgoing email message. The body of outgoing email is not recorded in the table.

### pins

Stores PIN codes used for registration of new controllers. **TODO: Link to docs about key-based authentication.**

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`                 | integer   | not null |                |
| `pin`                | integer   | not null |                |
| `code`               | text(80)  | not null |                |
| `creation_timestamp` | timestamp | not null |                |
| `enter_timestamp`    | timestamp |          |                |
| `user_id`            | integer   |          | `users.id`     |
| `controller_id`      | integer   |          | `resources.id` |
| `key_created`        | boolean   |          |                |
| `attributes`         | text      | not null |                | JSON object with additional attributes; currently always `{}`

### resource\_revisions

Contents of non-folder resources. Each resource is versioned; when a new value is written, it is recorded as a new row in this table. See "The Resource Hierarchy" above.

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`          | integer   | not null |                |
| `resource_id` | integer   | not null | `resources.id` |
| `timestamp`   | timestamp | not null |                |
| `data`        | binary    |          |                | See below

`data` holds the contents of resources under a certain size. Larger resources are stored using an external storage manager (in the filesystem or on S3, for example) in which case `data` is null.

For numeric sequences, `data` contains an ASCII representation of the number in decimal form.

For text sequences, `data` contains the text string in UTF-8 encoding. (But the rule about large contents applies; sufficiently large values of text sequences are kept in external storage.)

### resource\_views

Holds per-user preferences for viewing individual resources, e.g., sort order for the items in a folder.

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`          | integer | not null |                |
| `resource_id` | integer | not null | `resources.id` |
| `user_id`     | integer | not null | `users.id`     |
| `view`        | text    | not null |                | JSON object with resource-specific settings; semantics are defined by the front end

### resources

Metadata about resources. Every resource, whether it's a folder or a file or a sequence, has a row in this table. See "The Resource Hierarchy" above.

The hierarchy is represented using the `parent_id` column.

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`                     | integer   | not null |                |
| `last_revision_id`       | integer   |          |                |
| `organization_id`        | integer   |          | `resources.id` | ID of the root folder containing this resource (which is always an organization folder)
| `creation_timestamp`     | timestamp |          |                |
| `modification_timestamp` | timestamp |          |                |
| `parent_id`              | integer   |          | `resources.id` | This resource's immediate parent folder
| `name`                   | text      | not null |                | Resource name; must be unique for a given `parent_id` if `deleted` is not true
| `type`                   | integer   | not null |                | Numeric resource type; see below
| `permissions`            | text      |          |                | JSON list of lists; see "Permissions" section above
| `system_attributes`      | text      | not null |                | JSON object with system-defined keys; see below
| `user_attributes`        | text      |          |                | JSON object with additional user-defined values
| `deleted`                | boolean   | not null |                | If true, this resource is ignored in queries and its name may be reused
| `hash`                   | text(50)  |          |                | Legacy; use the `hash` system attribute instead (see below)
| `size`                   | bigint    |          |                | Legacy; use the `size` system attribute instead (see below)

The `permissions` column is a JSON array. See the "Permissions" section above for more details.

The `type` column is a numeric code with one of the following values. See "The Resource Hierarchy" above for more information about resource types.

| ID  | Description
| --- | ---
| 10  | Basic folder
| 11  | Organization folder
| 12  | Controller folder
| 13  | Remote folder (no longer used; should never appear)
| 20  | File
| 21  | Sequence
| 22  | App (soon to be removed)

The `system_attributes` column is a JSON object. The following keys are recognized.

| Key | Description
| --- | ---
| `data_type` | For sequences, the data type of the payload; see below.
| `decimal_places` | For sequences with numeric `data_type`, the number of significant digits after the decimal point.
| `max_history` | The number of revisions to retain for this resource; older ones are pruned from the database.
| `units` | For numeric sequences, what unit of measurement the number represents.
| `min_storage_interval` | For sequences, the minimum number of seconds allowed between updates. Updates that arrive before the interval are ignored.
| `full_name` | For organization folders, the human-readable display name of the organization; unlike the `name` column it may contain whitespace and upper-case letters.
| `timezone` | For organization folders, the [tz database name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) of the organization's primary time zone.
| `watchdog_recipients` | For controller folders, a comma-separated list of email addresses and phone numbers to send alerts to if the controller fails to send a watchdog message in the last `watchdog_minutes` minutes.
| `watchdog_minutes` | For controller folders, the amount of time to wait for watchdog messages before generating an alert. If not set or 0, no alerts are sent.
| `hash` | For file resources, the hexadecimal SHA-1 hash of the file contents.
| `size` | For file resources, the size of the file in bytes.

The `data_type` system attribute is required for sequence resources and must be one of the following.

| ID  | Description
| --- | ---
| 1   | Numeric sequence. Sequence values are interpreted as ASCII representations of numeric values. The number of decimal places is determined by the `decimal_places` system attribute.
| 2   | Text sequence. Sequence values are interpreted as Unicode strings.
| 3   | Image sequence. Sequence values are interpreted as base64-encoded binary blocks containing image data in JPEG format.

### thumbnails

For image sequences, a small thumbnail of the latest revision of the sequence.

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`          | integer | not null |                |
| `resource_id` | integer | not null | `resources.id` |
| `width`       | integer | not null |                |
| `height`      | integer | not null |                |
| `format`      | text(4) | not null |                | Currently always `jpg`
| `data`        | binary  | not null |                | Image data in JPEG format

### usage

**Unused.**

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`              | integer  | not null |                |
| `organization_id` | integer  | not null | `resources.id` |
| `period`          | text(10) | not null |                |
| `message_count`   | bigint   | not null |                |
| `data_bytes`      | bigint   | not null |                |
| `attributes`      | text     | not null |                |

### users

Holds information about users.

Controllers are not listed here; they are represented as controller folders in the `resources` table and authenticated using the data in the `keys` table.

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`                 | integer   | not null |                |
| `user_name`          | text(50)  |          |                | Optional login name; email address may also be used to log in
| `email_address`      | text(100) | not null |                |
| `password_hash`      | text(128) | not null |                | See below
| `full_name`          | text(100) | not null |                |
| `info_status`        | text      | not null |                | JSON object with keys indicating which informational messages have already been shown to the user; currently unused
| `attributes`         | text      | not null |                | JSON object with additional attributes; currently unused
| `deleted`            | boolean   | not null |                | If true, user may not log in and user name may be reused
| `creation_timestamp` | timestamp | not null |                |
| `role`               | integer   | not null |                | See below

`password_hash` is the [bcrypt](https://en.wikipedia.org/wiki/Bcrypt) hash of the user's password plus a salt value from the server configuration.

`role` has one of the following values.

| ID  | Description
| --- | ---
| 0   | Standard user.
| 2   | System administrator. Organization administrators are indicated by `organization_user.is_admin`; this role is for administrators of the server as a whole.
