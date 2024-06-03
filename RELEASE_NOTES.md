# spotify_monitor release notes

This is a high-level summary of the most important changes. 

# Changes in 1.4 (24 May 2024)

**Features and Improvements**:

- **NEW:** Possibility to define output log file name suffix (**-y** / **--log_file_suffix**)
- **NEW:** Feature allowing to suppress repeating API or network related errors (check **ERROR_500_NUMBER_LIMIT**, **ERROR_500_TIME_LIMIT**, **ERROR_NETWORK_ISSUES_NUMBER_LIMIT** and **ERROR_NETWORK_ISSUES_TIME_LIMIT** variables)
- **IMPROVE:** Information about log file name visible in the start screen
- **IMPROVE:** Rewritten get_date_from_ts(), get_short_date_from_ts(), get_hour_min_from_ts() and get_range_of_dates_from_tss() functions to automatically detect if time object is timestamp or datetime

**Bug fixes**:

- **BUGFIX:** Fixed issues with sporadic broken links in HTML emails (vars with special characters are now escaped properly)

# Changes in 1.3 (18 May 2024)

**Features and Improvements**:

- **NEW:** Full support for real-time playing of tracked songs (**-g**) in Spotify client in **Linux**
- **NEW:** Rewritten code for playing tracked songs (**-g**) in Spotify client in **macOS**
- **NEW:** New way of playing tracked songs (**-g**) in Spotify client in **Windows**
- **IMPROVE:** Improvements for running the code in Python under Windows
- **IMPROVE:** Better checking for wrong command line arguments
- **IMPROVE:** pep8 style convention corrections

**Bug fixes**:

- **BUGFIX:** Improved exception handling for some functions

# Changes in 1.2 (07 May 2024)

**Features and Improvements**:

- **NEW:** Possibility to define SP_DC_COOKIE via command line argument (-u / --spotify_dc_cookie)
- **IMPROVE:** SPOTIFY_ACTIVITY_CHECK and -p / --online_timer parameter have been removed as it only complicated the code with no visible benefit; SPOTIFY_INACTIVITY_CHECK is used in all places now, so user is considered active if the time of last activity is <= SPOTIFY_INACTIVITY_CHECK
- **IMPROVE:** Email sending function send_email() has been rewritten to detect invalid SMTP settings
- **IMPROVE:** Strings have been converted to f-strings for better code visibility
- **IMPROVE:** Info about CSV file name in the start screen

# Changes in 1.1 (30 Apr 2024)

**Features and Improvements**:

- **NEW:** Support for detection of songs listened on loop; if user plays the same song consecutively SONG_ON_LOOP_VALUE times (3 by default, configurable in the .py file) then there will be proper message on the console + you can get email notification (new -x / --song_on_loop_notification parameter); the alarm is triggered only once, when the SONG_ON_LOOP_VALUE is reached and once the user changes the song the timer is zeroed
- **NEW:** Feature to detect skipped songs; if the user plays the song for <= SKIPPED_SONG_THRESHOLD (0.6 by default = 60%, configurable in the .py file) of track duration, then the song is treated as skipped with proper message on the console & email notifications
- **NEW:** Information about number of listened songs in the session (console + notification emails)
- **IMPROVE:** Adding info about Artist and Album context of listened songs to notification emails
- **IMPROVE:** Adding info about Artist and Album context URLs in the console & email notifications
- **IMPROVE:** Information about readjusting session start due to too low inactivity timer is also in the notification email now

# Changes in 1.0 (23 Apr 2024)

**Features and Improvements**:

- **NEW:** Support for detecting Artist context of listened songs
- **IMPROVE:** Additional search/replace strings to sanitize tracks for Genius URLs

**Bug fixes**:

- **BUGFIX:** Fix for "SyntaxWarning: invalid escape sequence '\d'" in regexps
