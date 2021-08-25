#!/usr/bin/env/python3
import argparse
import logging
import sys
import time

from threading import Thread
from queue import Queue

import geoip2.database

from mcstatus import MinecraftServer

BAD_CHARACTERS = ("'", '"', "`", "\n")
CONNECT_TIMEOUT = 2
CSV_HEADER = "IP,Port,Country,Version,Online,Max,Ping,MOTD\n"
CSV_SEPARATORS = ("\t", ",", ";")
DATABASE_FILE = "geoip/GeoLite2-Country.mmdb"
DEFAULT_WORKER_COUNT = 4
LOG_DATE_FMT = "%Y/%m/%d %H:%M:%S"
LOG_FORMAT = "[%(asctime)s] %(message)s"


def worker(num, q_in, q_out):
    while q_in.qsize() > 0:
        ip, port = q_in.get()
        logging.debug("[Process %d] received %s to process" % (num, ip))
        try:
            server = MinecraftServer(ip, port)
            latency = int(server.ping())
            status = server.status()
            s_result = dict(ip=ip, port=port, latency=latency, version=status.version.name,
                            p_online=status.players.online, p_max=status.players.max, motd=status.description)
            q_out.put(s_result)
        except Exception as e:
            logging.debug("[Process %d] %s mcstatus exception: %s" % (num, ip, e))


def writer(data_queue, file_name, geoip):
    while True:
        data = data_queue.get()
        if data == -1:
            logging.debug("Writer process exit")
            break
        country = geoip.country(data["ip"]).country.name
        version = data["version"]
        for char in BAD_CHARACTERS:
            version = version.replace(char, "")
        for char in version:
            if char in CSV_SEPARATORS:
                version = '"{}"'.format(version)
                break
        row_data = tuple(
            str(x) for x in (
                data["ip"],
                data["port"],
                country,
                version,
                data["p_online"],
                data["p_max"],
                data["latency"],
                data["motd"]
            )
        )
        logging.info(
            "Server %s:%s from %s is using Minecraft version %s and has %s/%s players. Ping: %s MOTD: %s" % row_data)
        with open(file_name, "a") as f:
            f.write(",".join(row_data) + "\n")


def counter(task_queue, total):
    last_count = task_queue.qsize()
    while task_queue.qsize() > 0:
        tasks_count = task_queue.qsize()
        if tasks_count == last_count or last_count - tasks_count < 20:
            time.sleep(1)
        else:
            last_count = tasks_count
            done = total - tasks_count
            logging.info("Processed %d/%d hosts (%d%%)" % (done, total, round(done / total * 100, 1)))


def parse_args():
    parser = argparse.ArgumentParser(description="Scan for minecraft servers in IP list")
    parser.add_argument("input", help="Input file (masscan -oL result)")
    parser.add_argument("output", help="Output file")
    parser.add_argument("-d", "--debug", help="Enable debug output", action="store_true")
    parser.add_argument("-n", '--num-processes', help="Spawn N processes", type=int, required=False)
    args = parser.parse_args()
    return args.input, args.output, args.debug, args.num_processes


def read_hosts(file_name):
    hosts = []
    try:
        with open(file_name, 'r') as f:
            for line in f:
                if "open" in line:
                    data = line.split()
                    hosts.append((data[3], int(data[2]),))
    except FileNotFoundError:
        logging.critical("File not found")
        sys.exit(1)
    return hosts


def main():
    in_file, out_file, debug, num_proc = parse_args()
    if not num_proc:
        num_proc = DEFAULT_WORKER_COUNT
    if debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE_FMT, level=log_level)

    hosts = read_hosts(in_file)
    with open(out_file, "w") as f:
        f.write(CSV_HEADER)
    geoip2_reader = geoip2.database.Reader(DATABASE_FILE)

    task_queue = Queue()
    result_queue = Queue()
    worker_threads = [
        Thread(target=worker, args=(i, task_queue, result_queue,))
        for i in range(num_proc)
    ]
    writer_thread = Thread(target=writer, args=(result_queue, out_file, geoip2_reader,))
    for h in hosts:
        task_queue.put((h[0], h[1]))
    writer_thread.start()

    counter_thread = Thread(target=counter, args=(task_queue, len(hosts)))
    counter_thread.start()

    for process in worker_threads:
        process.start()
    for i, process in enumerate(worker_threads):
        process.join()
        logging.debug("Process %d joined" % i)
    result_queue.put(-1)
    counter_thread.join()
    writer_thread.join()


if __name__ == "__main__":
    main()
