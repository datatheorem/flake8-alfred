from time import sleep


def should_not_be_reported_0():
    time = 0
    sleep = 1


# Should be reported
sleep(1)

# Overwrite sleep, should not report anymore
sleep = 1
