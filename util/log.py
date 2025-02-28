import logging

logging.basicConfig(format='%(asctime)s %(levelname)s\t%(message)s')
 
class Whitelist(logging.Filter):
    def __init__(self, *whitelist):
        self.whitelist = [logging.Filter(name) for name in whitelist]

    def filter(self, record):
        return any(f.filter(record) for f in self.whitelist)