from timeit import default_timer as timer


class Timer:
    """
    timer.start() - start the timer
    timer.pause() - pause the timer
    timer.resume() - resume the timer
    timer.get() - return the current time
    """

    def __init__(self):
        self.time_started = 0.0
        self.time_paused = 0.0
        self.paused = False

    def start(self):
        """
        Starts an internal timer by recording the current time
        """
        self.time_started = timer()
        self.time_paused = 0.0
        self.paused = False

    def pause(self):
        """
        Pauses the timer
        """
        if not self.paused:
            self.time_paused = timer()
            self.paused = True

    def resume(self):
        """
        Resumes the timer by adding the pause time to the start time
        """
        if self.paused:
            pause_time = timer() - self.time_paused
            self.time_started = self.time_started + pause_time
            self.paused = False

    def get(self):
        """
        Returns a timedelta object showing the amount of time
        elapsed since the start time, less any pauses
        """
        if self.paused:
            return self.time_paused - self.time_started
        elif self.time_started == 0.0:
            return 0.0
        else:
            return timer() - self.time_started
