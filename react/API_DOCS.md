# Instagram Automation API

Simple REST API for controlling Instagram automation and monitoring status.

## Base URL
`http://localhost:5000` (default Flask development server)

## Endpoints

### Get Profiles
**GET** `/profiles`

Returns a list of all available profiles from Airtable.

**Request:**
- Method: GET
- Body: None

**Response:**
```json
[
  {
    "ads_power_id": "12345",
    "username": "instagram_username", 
    "profile_name": "Profile Display Name"
  }
]
```

**Example:**
```bash
curl http://localhost:5000/profiles
```

---

### Start All Profiles
**POST** `/start-all`

Starts automation for all profiles in Airtable.

**Request:**
- Method: POST
- Content-Type: `application/json` (optional)
- Body: `{"maxWorkers": 8}` (optional)

**Parameters:**
- `maxWorkers` (integer, optional): Number of concurrent profiles to process. Default: 4. Must be positive integer.

**Response:**
- Success: `{}` (empty object)
- Error: `{"error": "invalid_input", "message": "maxWorkers must be a positive integer"}` (400)
- Error: `{"error": "internal_error", "message": "Failed to start agents"}` (500)

**Examples:**
```bash
# Start with default 4 workers
curl -X POST http://localhost:5000/start-all

# Start with 8 concurrent workers
curl -X POST http://localhost:5000/start-all \
  -H "Content-Type: application/json" \
  -d '{"maxWorkers": 8}'
```

---

### Start Selected Profiles
**POST** `/start-selected`

Starts automation for specific profiles by AdsPower profile IDs.

**Request:**
- Method: POST
- Content-Type: `application/json`
- Body: `{"adsPowerIds": ["profile_id_1", "profile_id_2"]}`

**Response:**
- Success: `{}` (empty object)
- Error: `{"error": "invalid_input", "message": "AdsPowerIds List not found"}` (400)
- Error: `{"error": "internal_error", "message": "Failed to start selected agents"}` (500)

**Example:**
```bash
curl -X POST http://localhost:5000/start-selected \
  -H "Content-Type: application/json" \
  -d '{"adsPowerIds": ["12345", "67890"]}'
```

---

### Get Status
**GET** `/status`

Returns real-time status of all automation processes. Use for polling live updates.

**Request:**
- Method: GET
- Body: None

**Response:**
```json
{
  "activeProfiles": {
    "profile_id": {
      "ads_power_id": "12345",
      "username": "instagram_username",
      "bot_status": "running",
      "total_accounts": 100,
      "total_followed": 45,
      "total_follow_failed": 5,
      "total_already_followed": 10
    }
  },
  "scheduled": ["profile_id_1", "profile_id_2"]
}
```

**Bot Status Values:**
- `scheduled` - Profile is queued to start
- `running` - Currently following users
- `done` - Completed successfully
- `failed` - General failure
- `seleniumFailed` - Browser automation failed
- `adsPowerFailed` - Failed to start browser profile
- `accountSuspended` - Failed to start browser profile
- `accountLoggedOut` - Failed to start browser profile
- `followblocked` - Instagram blocked following
- `notargets` - No target users found

**Example:**
```bash
curl http://localhost:5000/status
```

---

## Frontend Implementation Notes

1. **Polling for Updates**: Call `/status` every 2-3 seconds to get live updates
2. **Error Handling**: All endpoints return JSON error objects with `error` and `message` fields
3. **Profile IDs**: Use AdsPower profile IDs (strings) for the `start-selected` endpoint
4. **Status Tracking**: Monitor `bot_status` field for each profile to track progress
