# spotify_monitor

spotify_monitor is a Python script which allows for real-time monitoring of Spotify friends music activity. 

## Features

- Real-time monitoring of songs listened by Spotify friend (including detection when user gets online & offline)
- Information about how long the user listened to a song
- Information about context of listened song (playlist/artist/album) with clickable URLs
- Email notifications for different events (user gets active/inactive, specific/all songs, errors)
- Saving all listened songs with timestamps to the CSV file
- Clickable Apple Music and Genius search URLs printed in the console & included in email notifications
- Showing basic statistics for user's playing session (how long, time span)
- Possibility to control the running copy of the script via signals

<p align="center">
   <img src="./assets/spotify_monitor.png" alt="spotify_monitor_screenshot" width="80%"/>
</p>

## Change Log

Release notes can be found [here](RELEASE_NOTES.md)

## Disclaimer

I'm not a dev, project done as a hobby. Code is ugly and as-is, but it works (at least for me) ;-)

## Requirements

The script requires Python 3.x.

It requires requests, python-dateutil and urllib3.

It has been tested succesfully on Linux (Raspberry Pi Bullseye & Bookworm based on Debian) and Mac OS (Ventura & Sonoma). 

Should work on any other Linux OS and Windows with Python.

## Installation

Install the required Python packages:

```sh
python3 -m pip install requests python-dateutil urllib3
```

Or from requirements.txt:

```sh
pip3 install -r requirements.txt
```

Copy the *spotify_monitor.py* file to the desired location. 

You might want to add executable rights if on Linux or MacOS:

```sh
chmod a+x spotify_monitor.py
```

## Configuration

Edit the *spotify_monitor.py* file and change any desired configuration variables in the marked **CONFIGURATION SECTION** (all parameters have detailed description in the comments).

### Spotify sp_dc cookie

Log in to Spotify web client [https://open.spotify.com/](https://open.spotify.com/) in your web browser and copy the value of sp_dc cookie to **SP_DC_COOKIE** variable. 

You can use Cookie-Editor by cgagnier to get it easily (available for all major web browsers): [https://cookie-editor.com/](https://cookie-editor.com/)

Newly generated Spotify's sp_dc cookie should be valid for 1 year. You will be informed by the tool once the cookie expires (proper message on the console and in email if errors notifications have not been disabled).

It is suggested to create a new Spotify account for usage with the tool since we are not using official Spotify Web API (it does not support fetching friend activity).

### Following the monitored user

You need to follow the user you want to monitor as a friend. 

Your friend needs to have sharing of listening activity enabled in their Spotify client.

### SMTP settings

If you want to use email notifications functionality you need to change the SMTP settings (host, port, user, password, sender, recipient).

### Other settings

All other variables can be left at their defaults, but feel free to experiment with it.

## Getting started

### List of supported parameters

To get the list of all supported parameters:

```sh
./spotify_monitor.py -h
```

or 

```sh
python3 ./spotify_monitor.py -h
```

### Monitoring mode

To monitor specific user activity, just type its Spotify user URI ID as parameter (**misiektoja** in the example below):

```sh
./spotify_monitor.py misiektoja
```

The tool will run infinitely and monitor the user until the script is interrupted (Ctrl+C) or killed the other way.

You can monitor multiple Spotify friends by spawning multiple copies of the script. 

It is suggested to use sth like **tmux** or **screen** to have the script running after you log out from the server.

The tool automatically saves its output to *spotify_monitor_userid.log* file (can be changed in the settings or disabled with -d).

Keep in mind that monitoring reports the listened track AFTER the user finishes listening to it. It is how activities are reported by Spotify. 

### How to get friend's user URI ID

The easiest way is to use your Spotify client. Go to the profile page of your friend and then click 3 dots and select 'Copy link to profile'. In my case it is: [https://open.spotify.com/user/misiektoja](https://open.spotify.com/user/misiektoja)

Then use the string after */user/* (*misiektoja* in the example) as your friend user URI ID.

You can also easily get user URI IDs for all your followed friends by using [Listing mode](#listing-mode).

### Listing mode

There is also other mode of the tool which prints the list of all your followed friends with their recently listened tracks (-l parameter):

```sh
./spotify_monitor.py -l
```

It also displays your friends Spotify username (very often first and last name of the user) and user URI ID (very often string of random characters). The latter one should be used as parameter to monitor the user.

<p align="center">
   <img src="./assets/spotify_monitor_listing.png" alt="spotify_monitor_listing" width="75%"/>
</p>

In my case both values are the same.

You can use the -l functionality regardless if the monitoring is used or not (it does not interfere). 

## How to use other features

### Email notifications

If you want to get email notifications once user gets active (-a) and inactive (-i):

```sh
./spotify_monitor.py misiektoja -a -i
```

Make sure you defined your SMTP settings earlier (see [SMTP settings](#smtp-settings)).

Example email:

<p align="center">
   <img src="./assets/spotify_monitor_email_notifications.png" alt="spotify_monitor_email_notifications" width="65%"/>
</p>

If you also want to be informed every time a user listens to specific songs, you can use **track_notification** functionality (-t). 

For that you need to create a file with list of songs you want to track (one track/album/playlist per line). The file needs to be indicated by -s parameter. The script checks if the listened track, album or playlist is in the file. Example file *spotify_tracks_misiektoja*:

```
we fell in love in october
Like a Stone
Half Believing
Something Changed
I Will Be There
```

Then run the tool with -t & -s parameters:

```sh
./spotify_monitor.py misiektoja -t -s ./spotify_tracks_misiektoja
```

If you want to get email notifications for every listened song (-j):

```sh
./spotify_monitor.py misiektoja -j
```

### Saving listened songs to the CSV file

If you want to save all the listened songs in the CSV file, use -b parameter with the name of the file (it will be automatically created if it does not exist):

```sh
./spotify_monitor.py misiektoja -b spotify_tracks_misiektoja.csv
```

### Automatic playing of tracks listened by the user in Spotify client

If you want the script to automatically track what the user listens and to play it in your Spotify client (-g):

```sh
./spotify_monitor.py misiektoja -g
```

Currently the script only supports playing the songs in Spotify client in Mac OS. There are conditionals in the code prepared for Linux and Windows, so feel free to test it and add proper commands.

Keep in mind that monitoring reports the listened track AFTER the user finishes listening to it. It is how activities are reported by Spotify. It means you will be one song behind the monitored user.

If you want to have more real-time monitoring of user's music activity, ask your friend to connect their Spotify account with [Last.fm](https://www.last.fm/) and then use the other tool I developed: [lastfm_monitor](https://github.com/misiektoja/lastfm_monitor).

### Check intervals and offline timer 

If you want to change the check interval to 20 seconds (-c):

```sh
./spotify_monitor.py misiektoja -c 20
```

If you want to change the time required to mark the user as inactive to 15 mins - 900 seconds (the timer starts from the last reported track):

```sh
./spotify_monitor.py misiektoja -o 900
```

### Controlling the script via signals


The tool has several signal handlers implemented which allow to change behaviour of the tool without a need to restart it with new parameters.

List of supported signals:

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle email notifications when user gets active/inactive |
| USR2 | Toggle email notifications for every song |
| CONT | Toggle email notifications for tracked songs |
| TRAP | Increase the inactivity check timer (by 30 seconds) |
| ABRT | Decrease the inactivity check timer (by 30 seconds) |

So if you want to change functionality of the running tool, just send the proper signal to the desired copy of the script.

I personally use **pkill** tool, so for example to toggle email notifications for every listened song, for the tool instance monitoring the *misiektoja* user:

```sh
pkill -f -USR2 "python3 ./spotify_monitor.py misiektoja"
```

### Other

Check other supported parameters using -h.

You can of course combine all the parameters mentioned earlier together (in monitoring mode, listing mode only supports -l).

## Limitations

Currently the ***'track_songs'*** functionality (-g parameter) only supports playing the songs in Spotify client in Mac OS. There are conditionals in the code prepared for Linux and Windows, so feel free to test it and add proper commands.

## Colouring log output with GRC

If you use [GRC](https://github.com/garabik/grc) and want to have the output properly coloured you can use the configuration file available [here](grc/conf.monitor_logs)

Change your grc configuration (typically *.grc/grc.conf*) and add this part:

```
# monitoring log file
.*_monitor_.*\.log
conf.monitor_logs
```

Now copy the *conf.monitor_logs* to your .grc directory and spotify_monitor log files should be nicely coloured.

## License

This project is licensed under the GPLv3 - see the [LICENSE](LICENSE) file for details
