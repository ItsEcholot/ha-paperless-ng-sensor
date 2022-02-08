# Home Assistant Paperless-NG Sensor

This custom integration adds a sensor with the following attributes:

- `document_tags`: List of Tags defined in Paperless.
- `document_total_count`: Number of total documents defined in Paperless.
- `document_tag_count`: Dictionary of all tags as the keys and the document count of this tag as the value.
- `document_todo`: List of documents that have been tagged with the configured **Todo** tag.
- `document_todo_count`: Count of documents that have been tagged with the configured **Todo** tag.
- `document_todo_tag_name`: The configured **Todo** tag as a string.

This integration uses the new config flow of HomeAssistant and thus is configured by using the `Add Integration` button.