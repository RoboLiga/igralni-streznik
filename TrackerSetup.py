from sledilnik.TrackerSetup import TrackerSetup

trackerSetup = TrackerSetup()
trackerSetup.file_names_config.video_source = 'http://192.168.1.117/mjpg/video.mjpg'
trackerSetup.start()
