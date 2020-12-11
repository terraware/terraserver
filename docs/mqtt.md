# MQTT messaging API

The system listens for MQTT messages for changes to device status and events. Clients may subscribe to MQTT topics to get real-time updates. The system is not itself an MQTT broker; rather, it communicates with an external broker such as Mosquitto.

## Topics

The MQTT topic hierarchy is the same as the resource hierarchy and has the following path elements.

1. Organization folder name, 1 path element.
2. Controller folder name, 1 path element. **Q: Is this always a direct child of the org?**
3. Device group, 1 or more path elements. **Q: I am not sure what the correct term for this is**
4. Device identifier, 1 path element.

So, for example, a topic of `treehuggers/easterisland/quarry/moai-1` would mean the device `moai-1` in the quarry at the Treehuggers organization's Easter Island site.

For messages that don't pertain to individual devices, only the first two path elements are included in the topic, e.g., `treehuggers/easterisland`.

## Authentication

The system authenticates to the MQTT broker by generating an auth token and presenting it as the password with a username of `token`. The token is always a string value with comma-delimited fields:

1. `0`
2. Integer POSIX timestamp
3. `0` (this is nonzero when users connect to the broker, but always zero when the server connects)
4. A 10-character random alphanumeric nonce
5. See below

The last field is the base64 encoding of the SHA-512 hash of the UTF-8 encoding of a string with the following comma-delimited fields:

1. The timestamp value from field 2 of the enclosing message
2. The value of field 3 of the enclosing message (`0`)
3. The value of field 4 of the enclosing message (the 10-character nonce)
4. A salt string, configured in the server settings
5. Nothing (final field is empty, that is, the string ends with a comma; this is nonempty when users connect to the broker but empty for the server)

On the broker side, the token is checked against the database using a custom [authentication plugin for Mosquitto](https://github.com/terraware/terraware-server/tree/master/mqtt_auth).

## Payload formats

The system accepts incoming messages in two formats: JSON and short. If the first character of the payload is `{`, it is treated as JSON.

### JSON messages

A JSON payload must be an object with zero or more fields. Each field identifies a particular type of message. Multiple messages of different types may be combined into a single payload. **Q: This is how the code currently works; you could have a single MQTT message with both `watchdog` and `send_email` fields. I think that is probably something we should treat as an error instead.**

The following fields are recognized in messages whose topics only include the first two path elements.

* `send_email`
* `send_sms`
* `watchdog`
  
The following fields are recognized in messages whose topics include all four path elements.

* `update`

#### send\_email

This field causes the server to send email. The value is an object with the following fields.

| Name | Type | Required? | Description
| --- | --- | --- | ---
| `emailAddresses` or `email_addresses` | string | *Yes* | Recipient address.
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
* Though the `emailAddresses` field name is plural, the system only supports sending to a single address.
* A single attempt is made to deliver the message.
* The server enforces a rate limit and silently ignores this message if there have been too many of them recently.
* The message is recorded in the `outgoing_messages` table (unless the request exceeds the rate limit).
* The body is included twice in the email, once as the main content and once as an attachment of type `text/plain`. **Q: Why does it do this?**

#### send\_sms

This field causes the server to send a text message. The value is an object with the following fields.

| Name | Type | Required? | Description
| --- | --- | --- | ---
| `phoneNumbers` or `phone_numbers` | string | *Yes* | Recipient phone number in [E.123 international notation](https://en.wikipedia.org/wiki/E.123).
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
* Though the `phoneNumbers` field is plural, the system only supports sending to a single recipient.
* A single attempt is made to deliver the message to Twilio. Twilio itself will retry delivery if there's a problem with the cellular infrastructure.
* The server enforces a rate limit and silently ignores this message if there have been too many of them recently.
* The message is recorded in the `outgoing_messages` table (unless the request exceeds the rate limit).

#### update

This field causes the server to record new values from the device specified in the message's topic.

The value of the `update` field is a single JSON object with string name/value pairs representing the updated data from the device.

In that inner object, the name `$t` is reserved. If present, it must contain a date and time in ISO-8601 extended format including time zone, and represents the time the values were read from the device. If there is no `$t` present, the server uses the date and time it received the message from the MQTT broker.

**Q: Should we explicitly reserve names that start with dollar signs, so we can add more later if needed?**

Values from devices are represented as sequence resources in the data model. Each sequence resource has a type, which is configured server-side.

In the JSON payload, values from devices must always be represented as strings, but the strings may be interpreted differently depending on the sequence's configured data type.

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

This field causes the server to record that it has received a message from the controller named by the message topic. The value is ignored.

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
