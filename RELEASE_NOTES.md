# spotify_monitor release notes

This is a high-level summary of the most important changes. 

# Changes in 1.3 (17 May 2024)

**Features and Improvements**:

- Full support for real-time playing of tracked songs (**-g**) in Spotify client in **Linux**
- New way of playing tracked songs (**-g**) in Spotify client in **Windows**
- Rewritten code for playing tracked songs (**-g**) in Spotify client in **macOS**
- Improvements for running the code in Python under Windows
- Better checking for wrong command line arguments

**Bugfixes**:

- Improved exception handling for some functions

# Changes in 1.2 (07 May 2024)

**Features and Improvements**:

- Possbility to define SP_DC_COOKIE via command line argument (-u / --spotify_dc_cookie)
- SPOTIFY_ACTIVITY_CHECK and -p / --online_timer parameter have been removed as it only complicated the code with no visible benefit; SPOTIFY_INACTIVITY_CHECK is used in all places now, so user is considered active if the time of last activity is <= SPOTIFY_INACTIVITY_CHECK
- Email sending function send_email() has been rewritten to detect invalid SMTP settings
- Strings have been converted to f-strings for better code visibility
- Info about CSV file name in the start screen

# Changes in 1.1 (30 Apr 2024)

**Features and Improvements**:

- New feature to detect songs listened on loop; if user plays the same song consecutively SONG_ON_LOOP_VALUE times (3 by default, configurable in the .py file) then there will be proper message on the console + you can get email notification (new -x / --song_on_loop_notification parameter); the alarm is triggered only once, when the SONG_ON_LOOP_VALUE is reached and once the user changes the song the timer is zeroed
- New feature to detect skipped songs; if the user plays the song for <= SKIPPED_SONG_THRESHOLD (0.6 by default = 60%, configurable in the .py file) of track duration, then the song is treated as skipped with proper message on the console & email notifications
- Information about number of listened songs in the session (console + notification emails)
- Adding info about Artist and Album context of listened songs to notification emails
- Adding info about Artist and Album context URLs in the console & email notifications
- Information about readjusting session start due to too low inactivity timer is also in the notification email now

# Changes in 1.0 (23 Apr 2024)

**Features and Improvements**:

- Support for detecting Artist context of listened songs
- Additional search/replace strings to sanitize tracks for Genius URLs

**Bugfixes**:

- Fix for "SyntaxWarning: invalid escape sequence '\d'" in regexes
