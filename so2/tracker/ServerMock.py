from multiprocessing import Process, Queue, freeze_support

from sledilnik.TrackerGame import TrackerGame

if __name__ == '__main__':
    freeze_support()
    queue = Queue()

    tracker = TrackerGame()
    tracker.file_names_config.video_source = 'ROBO_3.mp4'
    tracker.debug = True

    p = Process(target=tracker.start, args=(queue,))
    p.start()

    for _ in range(100):
        gameData = queue.get()
        print(gameData)
