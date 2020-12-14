# Data Model

## High-level concepts

### The resource hierarchy

The server can store arbitrary data in a filesystem-like hierarchy of folders.
The resources files and folders are accessed by URLs in the same way that file system
objects are accessed using paths. Each resource has a type:

* organization folder: the top-level folder corresponding to an organization
* controller folder: a folder corresponding to a controller
* basic folder: a folder that can contain other resources
* remote folder: **Q: What is this?**
* file: a text or binary file (image, CSV, markdown, etc.)
* sequence: a time series of values (numeric, string, or images)
* app: **Q: What is this?**

Non-folder resources (files and sequences) are represented as a time-ordered list of
resource revisions. In a sequence, these revisions are timestamped values of the time series.
A log file can be represented as a sequence of text values. In the case of files,
the revisions provide a history of previous versions of the file data or app specification.

Large resource revisions can be placed in bulk storage (e.g. S3). Small resource revisions are
placed directly in the server database.

#### Folder organization

Folders can be nested in an arbitrary hierarchy, subject to a few rules.

* The top-level resource is always an organization folder.
* Organization folders can only appear at the top level (that is, organizations can't be nested). **Q: Is this true?**
* At most one controller folder can appear in a path (that is, controllers can't be nested). **Q: Is this true? What would it mean to nest controllers?**
* Sequences and files whose data come from controllers must be descendents of a controller folder, but there can be additional basic folders between the controller folder and the sequence or file resource.

Typically, each physical device will be represented by a basic folder that contains the sequences and files with that device's data.

Putting all that together, the path to a sequence representing readings from a device that is managed by a controller has a structure like,

    /organization[/basic[/basic...]]/controller[/basic[/basic...]]/device/sequence

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
| `organization_name`  | text(100) |          |                |
| `organization_id`    | integer   |          | `resources.id` |
| `inviter_id`         | integer   |          | `users.id`     |
| `creation_timestamp` | timestamp | not null |                |
| `redeemed_timestamp` | timestamp |          |                |
| `access_code`        | text(40)  | not null |                | Randomly generated code
| `email_address`      | text      | not null |                |
| `email_sent`         | boolean   | not null |                |
| `email_failed`       | boolean   | not null |                |
| `attributes`         | text      | not null |                | **Q: What is this?**

### action\_throttles

Used for rate limiting of actions such as email alerts.

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`            | integer  | not null |                |
| `controller_id` | integer  |          | `resources.id` |
| `user_id`       | integer  |          | `users.id`     |
| `type`          | text(50) | not null |                |
| `recent_usage`  | text     | not null |                |

### controller\_status

Monitoring data for each controller, to allow for alerting if controllers die.

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`                         | integer   | not null | `resources.id` |
| `client_version`             | text(80)  | not null |                |
| `web_socket_connected`       | boolean   | not null |                |
| `last_connect_timestamp`     | timestamp |          |                |
| `last_watchdog_timestamp`    | timestamp |          |                | When the most recent watchdog heartbeat was receved from the controller
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

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`            | integer   | not null |                |
| `controller_id` | integer   |          | `resources.id` |
| `user_id`       | integer   |          | `users.id`     |
| `timestamp`     | timestamp | not null |                |
| `recipients`    | text      | not null |                |
| `message`       | text      | not null |                |
| `attributes`    | text      | not null |                |

### pins

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
| `attributes`         | text      | not null |                |

### resource\_revisions

Payloads of non-folder resources. For sequence resources, there may be multiple revisions with a single resource ID. See "The Resource Hierarchy" above.

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`          | integer   | not null |                |
| `resource_id` | integer   | not null | `resources.id` |
| `timestamp`   | timestamp | not null |                |
| `data`        | binary    |          |                |

### resource\_views

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`          | integer | not null |                |
| `resource_id` | integer | not null | `resources.id` |
| `user_id`     | integer | not null | `users.id`     |
| `view`        | text    | not null |                |

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
| `hash`                   | text(50)  |          |                |
| `size`                   | bigint    |          |                |

The `permissions` column is a JSON array. See the "Permissions" section above for more details.

The `type` column is a numeric code with one of the following values. See "The Resource Hierarchy" above for more information about resource types.

| ID  | Description
| --- | ---
| 10  | Basic folder
| 11  | Organization folder
| 12  | Controller folder
| 13  | Remote folder
| 20  | File
| 21  | Sequence
| 22  | App

The `system_attributes` column is a JSON object. The following keys are recognized.

| Key | Description
| --- | ---
| `data_type` | For sequences, the data type of the payload; see below.
| `decimal_places` | For sequences with numeric `data_type`, the number of significant digits after the decimal point.
| `max_history` | The number of revisions to retain for this resource; older ones are pruned from the database.
| `units` | For numeric sequences, what unit of measurement the number represents.
| `min_storage_interval` | For sequences, the minimum number of seconds allowed between updates. Updates that arrive before the interval are ignored.
| `remote_path` | For remote folder resources, **Q: What does this mean?**
| `controller_id` | For remote folder resources, **Q: What does this mean?**
| `full_name` | For organization folders, the human-readable display name of the organization; unlike the `name` column it may contain whitespace and upper-case letters.
| `timezone` | For organization folders, the [tz database name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) of the organization's primary time zone.
| `watchdog_recipients` | For controller folders, a comma-separated list of email addresses and phone numbers to send alerts to if the controller fails to send a watchdog message in the last `watchdog_minutes` minutes.
| `watchdog_minutes` | For controller folders, the amount of time to wait for watchdog messages before generating an alert. If not set or 0, no alerts are sent.
| `hash` | For file resources, the hexadecimal SHA-1 hash of the file contents. **Q: This appears to duplicate the `hash` column in the table; what is the difference?**
| `size` | For file resources, the size of the file in bytes. **Q: Same question as `hash`**

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

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`              | integer  | not null |                |
| `organization_id` | integer  | not null | `resources.id` |
| `period`          | text(10) | not null |                |
| `message_count`   | bigint   | not null |                |
| `data_bytes`      | bigint   | not null |                |
| `attributes`      | text     | not null |                |

### users

| Column | Type | Null | References | Notes
| --- | --- | --- | --- | ---
| `id`                 | integer   | not null |                |
| `user_name`          | text(50)  |          |                | Optional login name; email address may also be used to log in
| `email_address`      | text(100) | not null |                |
| `password_hash`      | text(128) | not null |                |
| `full_name`          | text(100) | not null |                |
| `info_status`        | text      | not null |                | JSON object with keys indicating which informational messages have already been shown to the user; currently unused
| `attributes`         | text      | not null |                | JSON object with additional attributes; currently unused
| `deleted`            | boolean   | not null |                | If true, user may not log in and user name may be reused
| `creation_timestamp` | timestamp | not null |                |
| `role`               | integer   | not null |                | See below

The `role` column has one of the following values.

| ID  | Description
| --- | ---
| 0   | Standard user.
| 2   | System administrator. Organization administrators are indicated by `organization_user.is_admin`; this role is for administrators of the server as a whole.
