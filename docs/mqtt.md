# MQTT messaging API

The system listens for MQTT messages for changes to device status and events. Clients may subscribe to MQTT topics to get real-time updates. The system is not itself an MQTT broker; rather, it communicates with an external broker such as Mosquitto.

## Topics

Clients can use the MQTT broker to send and receive arbitrary messages to each other, and can use whatever naming scheme they like for the topics of such messages.

The server pays attention to messages whose topics are the paths of folders in the resource hierarchy. The resources data model allows an arbitrary tree of folders, but typically, resource folders will be arranged in an ordered hierarchy like this:

1. Organization folder name, typically 1 path element.
2. Controller folder name, typically 1 path element. This usually corresponds to a site.
3. Device group, 1 or more path elements. This might group devices by type and/or by location within a site.
4. Device identifier, typically 1 path element. This groups together the individual resources associated with a single device.

So, for example, a topic of `treehuggers/easterisland/quarry/moai-1` would mean the device `moai-1` in the quarry at the Treehuggers organization's Easter Island site.

The server ignores any message whose topic isn't the path of a folder resource.

## Authentication

Clients and the Terraware server have to authenticate themselves to the MQTT broker to publish and receive messages. [A custom authentication plugin for Mosquitto](/mqtt_auth) implements the authentication scheme described here.

There are two authentication schemes, token-based and key-based.

### Token authentication

Token-based authentication is used by browser clients and Terraware Server itself. They both act as clients from the MQTT broker's point of view.

An MQTT client authenticates to the MQTT broker by generating an auth token and presenting it as the password with a username of `token` during the initial MQTT connection handshake. The token is always a string value with comma-delimited fields:

1. Version number, currently always `0`
2. Integer POSIX timestamp
3. User ID, always `0` for server-initiated connections
4. A 10-character random alphanumeric nonce
5. See below

The last field is the base64 encoding of the SHA-512 hash of the UTF-8 encoding of a string with the following comma-delimited fields:

1. The timestamp value from field 2 of the enclosing message
2. The user ID (`0` for server-initiated connections)
3. The value of field 4 of the enclosing message (the 10-character nonce)
4. A salt string, configured in the server settings
5. For user-initiated connections, a salted hash of the user's password. This field is empty for server-initiated connections. **TODO: Document password hashing.**

### Key authentication

Key-based authentication is used by controllers.

**TODO: Document key-based authentication, including why it's used on controllers.**

## Payload formats

The system accepts incoming messages in two formats: JSON and short. If the first character of the payload is `{`, it is treated as JSON.

### JSON messages

A JSON payload must be an object with exactly one field. The name of the field determines the message type. The following message types are recognized.

* `send_email`
* `send_sms`
* `update`
* `watchdog`

#### send\_email

This field causes the server to send email. The message topic must be the path of a controller folder. The value is an object with the following fields.

| Name | Type | Required? | Description
| --- | --- | --- | ---
| `email_addresses` | string | *Yes* | Recipient address.
| `subject` | string | *Yes* | Subject line.
| `body` | string | *Yes* | Message body.

Example payload:

```json
{
  "send_email": {
    "emailAddresses": "user@example.com",
    "subject": "Your attention is urgently required",
    "body": "Hello, I am a prince and want to send you a million dollars"
  }
}
```

Behavior notes:

* The sender's name and address are server configuration options and cannot be set on a per-message basis.
* Though the `email_addresses` field name is plural, the system only supports sending to a single address. (CU-h8w9mc)
* A single attempt is made to deliver the message.
* The server enforces a rate limit and silently ignores this message if there have been too many of them recently.
* The message is recorded in the `outgoing_messages` table (unless the request exceeds the rate limit).
* The body is included twice in the email, once as the main content and once as an attachment of type `text/plain`. (CU-h8wd7v)

#### send\_sms

This field causes the server to send a text message. The message topic must be the path of a controller folder. The value is an object with the following fields.

| Name | Type | Required? | Description
| --- | --- | --- | ---
| `phone_numbers` | string | *Yes* | Recipient phone number in [E.123 international notation](https://en.wikipedia.org/wiki/E.123).
| `message` | string | *Yes* | Message body, up to 1600 characters.

Example payload:

```json
{
  "send_sms": {
    "phoneNumbers": "+1 212 555 1212",
    "message": "Your credit card has expired. Text us your Gmail password to renew it."
  }
}
```

Behavior notes:

* The sender's phone number is a server configuration option and cannot be set on a per-message basis.
* Though the `phone_numbers` field is plural, the system only supports sending to a single recipient. (CU-h8w9mc)
* A single attempt is made to deliver the message to Twilio. Twilio itself will retry delivery if there's a problem with the cellular infrastructure.
* The server enforces a rate limit and silently ignores this message if there have been too many of them recently.
* The message is recorded in the `outgoing_messages` table (unless the request exceeds the rate limit).

#### update

This field causes the server to record new values for some number of sequences. The message topic must be the path of a folder resource.

The value of the `update` field is a single JSON object with string name/value pairs representing the updated data from the device.

Names beginning with `$` are reserved for metadata. Currently, there is one such name defined, `$t`. If present, it must contain a date and time in ISO-8601 extended format including time zone, and represents the time the values were read from the device. If there is no `$t` field present, the server uses the date and time it received the message from the MQTT broker.

Values from devices are represented as sequence resources in the data model. Each sequence resource has a name and a type, which are configured server-side.

In the JSON payload, values from devices must always be represented as strings, but the strings may be interpreted differently depending on the sequence's configured data type.

Names of sequences are always relative to the folder specified by the message topic.

Example payload:

```json
{
  "update": {
    "$t": "2020-01-01T12:34:56.999999Z",
    "relative_state_of_charge": "2.7",
    "system_voltage": "1.76",
    "status_line": "All systems functioning"
  }
}
```

#### watchdog

This field causes the server to record that it has received a message from the controller named by the message topic. The topic must therefore be the path of a controller folder. The value is currently ignored and should be an empty JSON object.

### Short messages

A short message is a comma-separated list of values, whose message type is identified by the first element of the list.

#### Sequence update (type "s")

Update the value of a single sequence resource. This may be used to update any sequence, but is commonly used to store log messages in the database.

The message must contain exactly 4 fields.

1. The message type `s`
2. The sequence subpath, relative to the message topic (may not contain commas)
3. The timestamp of the new value in ISO-8601 extended format including time zone
4. The new sequence value (may contain commas)

Example payload:

```
s,log,2020-01-01T12:34:56.777777Z,INFO: Something happend and here's a log message about it
```

Behavior notes:

* Unlike the JSON-format `update` field, the topic is not validated at all; as long as the topic and sequence subpath combine to point to a sequence resource, the update is recorded.
