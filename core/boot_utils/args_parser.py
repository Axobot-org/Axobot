import argparse


def setup_start_parser():
    "Create a parser for the command-line interface"
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", "-t", help="The bot token to use", required=True)
    parser.add_argument("--entity-id", "-e", type=int, help="The entity ID to use, if no bot is specified by --token")
    parser.add_argument("--no-main-loop", help="Deactivate the bot main loop",
                        action="store_false", dest="event_loop")
    parser.add_argument("--no-rss", help="Disable any RSS feature (loop and commands)",
                        action="store_false", dest="rss_features")
    parser.add_argument("--count-open-files", help="Count the number of files currently opened by the process",
                        action="store_true", dest="count_open_files")

    return parser
