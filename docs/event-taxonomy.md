# Event taxonomy

Event types are `category.name` (snake_case).

| Category      | Event                          | Payload (typical)                       |
| ------------- | ------------------------------ | --------------------------------------- |
| `system`      | `session_start`                | (auto)                                  |
| `system`      | `session_end`                  | `end_reason`                            |
| `progression` | `level_start`                  | `level`                                 |
| `progression` | `level_complete`               | `level`, `stars`                        |
| `progression` | `level_fail`                   | `level`, `reason`                       |
| `economy`     | `currency_earn`                | `currency`, `amount`, `source`          |
| `economy`     | `currency_spend`               | `currency`, `amount`, `item`            |
| `economy`     | `iap`                          | `sku`, `price`, `currency`              |
| `gameplay`    | `action`                       | `action`, ...                           |
| `gameplay`    | `ability_used`                 | `ability`                               |
| `gameplay`    | `score`                        | `value`                                 |
| `error`       | `crash`                        | (sent via `/v1/crashes` typically)      |
| `error`       | `rage_quit`                    | `level`                                 |
| `custom`      | `<anything>`                   | arbitrary                               |
