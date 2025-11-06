# Design Document

## Overview

The admin voice mode toggle feature adds a system-wide setting that controls whether users can access "Talk Mode" when starting interviews. This feature integrates with the existing admin interface by adding a toggle control below the knowledge scopes section and persists the setting in a new database table called "settings". The implementation follows existing patterns in the Flask application for admin functionality, database operations, and UI components.

## Architecture

### High-Level Components

1. **Database Layer**: New `settings` table with generic key-value storage for system configuration
2. **Data Access Layer**: New methods in `Database` class for settings CRUD operations
3. **Admin Interface**: Enhanced admin routes and templates to display and manage the voice mode toggle
4. **Interview Interface**: Modified interview start logic to check voice mode availability
5. **Frontend Components**: HTMX-powered toggle control integrated into existing admin UI

### Integration Points

- **Existing Admin System**: Extends current admin.py routes and admin templates
- **Database Connection**: Uses existing Aurora PostgreSQL connection patterns
- **Authentication**: Leverages existing Cognito admin role authentication
- **UI Framework**: Integrates with current Bootstrap and HTMX implementation

## Components and Interfaces

### Database Schema

#### Settings Table

```sql
CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

**Initial Data**:

```sql
INSERT INTO settings (key, value) VALUES ('talk_mode_enabled', 'true')
ON CONFLICT (key) DO NOTHING;
```

### Data Models

#### Settings Operations

```python
class Database:
    def get_setting(self, key: str) -> Optional[str]:
        """Retrieve a setting value by key"""

    def set_setting(self, key: str, value: str) -> None:
        """Set or update a setting value"""

    def get_talk_mode_enabled(self) -> bool:
        """Get talk mode enabled status with default fallback"""
```

### API Endpoints

#### Admin Settings Routes

```python
@app.route("/admin/settings/talk-mode", methods=["POST"])
@login_required
@admin_required
def toggle_talk_mode():
    """Toggle talk mode setting via HTMX"""

@app.route("/admin/settings/talk-mode/status")
@login_required
@admin_required
def get_talk_mode_status():
    """Get current talk mode status for admin UI"""
```

#### Interview Interface Integration

```python
# Modified in existing interview routes
def get_interview_start_options(db: Database) -> dict:
    """Get available interview mode options based on settings"""
    talk_enabled = db.get_talk_mode_enabled()
    return {
        'type_mode': True,
        'talk_mode': talk_enabled
    }
```

### Frontend Components

#### Admin Toggle Control

```html
<!-- Added to admin.body.html -->
<div class="mt-5">
  <h6>System Settings</h6>
  <div class="form-check form-switch">
    <input
      class="form-check-input"
      type="checkbox"
      id="talkModeToggle"
      {%
      if
      talk_mode_enabled
      %}checked{%
      endif
      %}
      hx-post="/admin/settings/talk-mode"
      hx-target="#talk-mode-status"
    />
    <label class="form-check-label" for="talkModeToggle">
      Enable Talk Mode
    </label>
  </div>
  <div id="talk-mode-status" class="form-text">
    Talk Mode is currently {% if talk_mode_enabled %}enabled{% else %}disabled{%
    endif %}
  </div>
</div>
```

#### Interview Start Interface

```html
<!-- Modified interview start template -->
<div class="interview-mode-selection">
  <button class="btn btn-primary" data-mode="type">Type Mode</button>
  {% if talk_mode_enabled %}
  <button class="btn btn-secondary" data-mode="talk">Talk Mode</button>
  {% endif %}
</div>
```

## Data Models

### Settings Data Flow

1. **Default State**: Voice mode enabled (true) on fresh installation
2. **Admin Toggle**: Updates settings table via HTMX POST request
3. **Interview Check**: Queries settings table when user starts interview
4. **UI Rendering**: Templates receive voice mode status as context variable

### Database Operations Pattern

Following existing patterns in `database.py`:

```python
def get_setting(self, key: str) -> Optional[str]:
    query = "SELECT value FROM settings WHERE key = %s"
    with self.connect() as conn:
        result = conn.execute(query, (key,)).fetchone()
        return result[0] if result else None

def set_setting(self, key: str, value: str) -> None:
    query = """
        INSERT INTO settings (key, value, updated_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (key)
        DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
    """
    with self.connect() as conn:
        conn.execute(query, (key, value))
```

## Error Handling

### Database Errors

- **Connection Failures**: Use existing credential cache and retry patterns
- **Query Failures**: Log errors and return safe defaults (voice mode enabled)
- **Transaction Rollback**: Ensure settings updates are atomic

### Admin Interface Errors

- **Toggle Failures**: Display error message via HTMX response
- **Permission Errors**: Use existing admin_required decorator behavior
- **Network Issues**: Graceful degradation with current state display

### Interview Interface Errors

- **Settings Unavailable**: Default to voice mode enabled for backward compatibility
- **Database Timeout**: Cache last known state in application memory
- **Fallback Behavior**: Always show Type Mode, conditionally show Talk Mode

## Testing Strategy

### Unit Tests

- **Database Operations**: Test settings CRUD operations with mock database
- **Admin Routes**: Test toggle functionality with admin authentication
- **Interview Logic**: Test mode availability logic with different settings states

### Integration Tests

- **End-to-End Admin Flow**: Test complete toggle workflow from UI to database
- **Interview Start Flow**: Test interview mode selection with different settings
- **Database Migration**: Test settings table creation and initial data

### Manual Testing Scenarios

1. **Fresh Installation**: Verify voice mode enabled by default
2. **Admin Toggle**: Test enable/disable functionality and UI feedback
3. **User Experience**: Verify interview start options change based on setting
4. **Permission Testing**: Ensure non-admin users cannot access settings
5. **Database Persistence**: Verify settings survive application restarts

### Test Data Setup

```sql
-- Test with talk mode disabled
UPDATE settings SET value = 'false' WHERE key = 'talk_mode_enabled';

-- Test with talk mode enabled
UPDATE settings SET value = 'true' WHERE key = 'talk_mode_enabled';

-- Test with missing setting (should default to enabled)
DELETE FROM settings WHERE key = 'talk_mode_enabled';
```

## Implementation Notes

### Migration Strategy

1. **Database Migration**: Add settings table via existing `db-migrate.sh` process
2. **Backward Compatibility**: Default to voice mode enabled if setting doesn't exist
3. **Deployment Order**: Database changes first, then application code

### Performance Considerations

- **Settings Caching**: Consider in-memory cache for frequently accessed settings
- **Database Queries**: Minimal impact with single row lookups
- **UI Responsiveness**: HTMX provides immediate feedback without page refresh

### Security Considerations

- **Admin Only Access**: Settings modification restricted to admin role
- **Input Validation**: Boolean values validated on server side
- **Audit Trail**: Settings changes logged via existing audit mechanisms
