import logging
import subprocess
import sys
import time
import schedule


def subprocess_cmd(command):
    print("starting...")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    proc_stdout = process.communicate()[0].strip()
    print(proc_stdout)
    # logging.info(proc_stdout)


def cron_run_win():
    print("win...")
    print('start scraping... ####################################################################')
    subprocess_cmd('python C:/Users/Administrator/Desktop/Scraper/pulsepoint_scraper.py')


def cron_run_linux():
    print("Linux...")
    print('start scraping... ####################################################################')
    subprocess_cmd('python3 pulsepoint_scraper.py')

def cron_run_mac():
    print("Linux...")
    print('start scraping... ####################################################################')
    subprocess_cmd('python pulsepoint_scraper.py')


def cron_run():
    print("Waiting for tor...")
    print(sys.platform)
    time.sleep(60)
    if 'darwin' in sys.platform:
        cron_run_mac()
    elif 'win' in sys.platform:
        cron_run_win()
        schedule.every(4).minutes.do(cron_run_win)

    elif 'linux' in sys.platform:
        cron_run_linux()
        schedule.every(4).minutes.do(cron_run_linux)

    while True:
        schedule.run_pending()
        time.sleep(1)


cron_run()
