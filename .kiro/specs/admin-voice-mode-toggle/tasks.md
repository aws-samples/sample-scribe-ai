# Implementation Plan

- [x] 1. Create database migration for settings table
- [x] 1.1 Update local development database schema

  - Add settings table definition to web/database.sql for local development
  - Include CREATE TABLE statement with key, value, created_at, and updated_at columns
  - Add INSERT statement for initial talk_mode_enabled setting
  - _Requirements: 3.1, 3.3, 3.5_

- [x] 1.2 Create production database migration script

  - Create SQL migration script to add settings table with key-value structure
  - Include initial data insertion for talk_mode_enabled setting defaulted to true
  - Add migration to existing db-migrate.sh process
  - _Requirements: 3.1, 3.3, 3.5_

- [x] 2. Implement database layer for settings management
- [x] 2.1 Add settings CRUD methods to Database class

  - Implement get_setting() method for retrieving setting values by key
  - Implement set_setting() method for creating/updating setting values
  - Follow existing database connection and query patterns from database.py
  - _Requirements: 3.1, 3.2, 3.4, 4.3_

- [x] 2.2 Add talk mode specific helper method

  - Implement get_talk_mode_enabled() method with default fallback to True
  - Handle cases where setting doesn't exist in database
  - Return boolean value for easy template usage
  - _Requirements: 3.5, 4.4_

- [ ]\* 2.3 Write unit tests for settings database operations

  - Test get_setting() with existing and non-existing keys
  - Test set_setting() for both insert and update scenarios
  - Test get_talk_mode_enabled() with various database states
  - _Requirements: 3.1, 3.5_

- [x] 3. Create admin interface for talk mode toggle
- [x] 3.1 Add admin routes for talk mode management

  - Implement POST route for toggling talk mode setting
  - Implement GET route for retrieving current talk mode status
  - Use existing admin authentication and authorization patterns
  - Return HTMX-compatible responses for UI updates
  - _Requirements: 1.1, 1.4, 4.1, 4.2, 5.1, 5.4_

- [x] 3.2 Update admin template with talk mode toggle control

  - Add toggle switch control to admin.body.html below knowledge scopes section
  - Integrate with existing Bootstrap and HTMX patterns
  - Include status display and error handling elements
  - Pass talk_mode_enabled variable from admin route to template
  - _Requirements: 1.1, 1.2, 1.3, 5.1, 5.4_

- [x] 3.3 Update admin route to provide talk mode status

  - Modify existing admin() route to query talk mode setting from database
  - Pass talk_mode_enabled variable to template context
  - Handle database errors gracefully with appropriate fallbacks
  - _Requirements: 1.1, 4.4, 5.3_

- [ ]\* 3.4 Write integration tests for admin toggle functionality

  - Test complete toggle workflow from UI interaction to database update
  - Test admin authentication requirements for settings access
  - Test error handling and user feedback scenarios
  - _Requirements: 1.4, 4.2, 5.2_

- [x] 4. Integrate talk mode availability into interview interface
- [x] 4.1 Update interview start logic to check talk mode setting

  - Query talk mode enabled status from database in interview routes
  - Pass talk_mode_enabled variable to interview start templates
  - Ensure backward compatibility if setting is missing
  - _Requirements: 2.1, 2.2, 2.3, 4.4_

- [x] 4.2 Modify interview start templates to conditionally show talk mode

  - Update interview start template to show/hide Talk Mode button based on setting
  - Ensure Type Mode is always available regardless of setting
  - Maintain existing interview start workflow and styling
  - _Requirements: 2.1, 2.2, 2.3_

- [ ]\* 4.3 Write tests for interview mode availability logic

  - Test interview start options with talk mode enabled and disabled
  - Test template rendering with different talk mode settings
  - Test fallback behavior when database is unavailable
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 5. Add error handling and logging
- [x] 5.1 Implement error handling for settings operations

  - Add try-catch blocks around database operations with appropriate logging
  - Provide user-friendly error messages for admin interface failures
  - Ensure graceful degradation when database is unavailable
  - _Requirements: 5.2, 5.5_

- [x] 5.2 Add audit logging for settings changes

  - Log talk mode toggle changes using existing logging mechanisms
  - Include user information and timestamp in audit logs
  - Follow existing security and audit patterns
  - _Requirements: 4.5_

- [ ]\* 5.3 Write tests for error handling scenarios
  - Test behavior when database connection fails
  - Test error message display in admin interface
  - Test fallback behavior for interview start when settings unavailable
  - _Requirements: 5.2, 5.5_
