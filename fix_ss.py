""" Find and resolve bad transactions on MS Symbol Server
    https://msdn.microsoft.com/ru-ru/library/windows/desktop/ms681378(v=vs.85).aspx
"""
import argparse
from os import path

class Paths(object):
    """ constants """
    PATH_TO_SS = r'\\corp.wargaming.local\wgdfs\DepartExchange\Symbols'
    ADMIN = "000Admin"
    HISTORY = "history.txt"
    SERVER = "server.txt"
    LAST_TID = "lastid.txt"
    REFS = "refs.ptr"

class Version(object):
    """ program version description """
    STRING = '1.0'
    PRODUCT = 'fix_ss'

class TFile(object):
    """ transaction file """
    def __init__(self, ctx, line):
        row = line.split(',', 8)
        self.rel_path = row[0].strip("\"")
        self.origin_path = row[1].strip("\"")
        _, self.file_name = path.split(self.origin_path)
        def get_archive_name(name):
            """ aaa.exe -> aaa.ex_ """
            array = list(name)
            array.reverse()
            array[0] = '_'
            array.reverse()
            return "".join(array)
        self.archive_name = get_archive_name(self.file_name)
        self.ctx = ctx

    def full_path(self):
        """ get full path to file """
        folder_path = path.join(self.ctx.path_to_ss, self.rel_path)
        file_path = path.join(folder_path, self.file_name)
        if path.isfile(file_path):
            return file_path
        file_path = path.join(folder_path, self.archive_name)
        if path.isfile(file_path):
            return file_path
        return None

    def exists(self):
        """ verify file path """
        file_path = self.full_path()
        return file_path is not None


class Transaction(object):
    """ Transaction descriptor """
    def __init__(self, line, ctx):
        row = line.split(',', 8)
        self.tid = int(row[0])
        self.type = row[1]
        self.file = row[2]
        self.date = row[3]
        self.time = row[4]
        self.product = row[5].strip("\"")
        self.version = row[6].strip("\"")
        self.comment = row[7].strip("\"")
        self.ctx = ctx
        transaction_file_name = "{:010d}".format(self.tid)
        if self.type == "del":
            transaction_file_name = "{:010d}.deleted".format(self.tid)
        self.transaction_file_path = path.join(self.ctx.admin_path, transaction_file_name)

    def __str__(self):
        return "{:010d},{},{},{},{},\"{}\",\"{}\",\"{}\",".format(
            self.tid, self.type, self.file, self.date, self.time,
            self.product, self.version, self.comment
            )

    def exists(self):
        """ check if descriptor file exists """
        return path.isfile(self.transaction_file_path)

    def files(self):
        """ all files in the transaction """
        lines = []
        with open(self.transaction_file_path, 'r') as transaction_description_file:
            lines = transaction_description_file.readlines()
        for line in lines:
            yield TFile(self.ctx, line)


def main():
    """ program entry point """
    parser = argparse.ArgumentParser(description="Rescuer MS Symbol Server DB", prog=Version.PRODUCT)
    parser.add_argument('--version', action='version', version='%(prog)s {}'.format(Version.STRING))
    parser.add_argument('--path-to-ss', default=Paths.PATH_TO_SS, help='Path to Microsoft Symbol Server database')
    parser.add_argument('--show-only', action='store_true', help="Show problems. Don't fix")

    ctx = parser.parse_args()

    if not path.isdir(ctx.path_to_ss):
        print("Error: Wrong path: {}".format(ctx.path_to_ss))
        return

    print("Symbol Server: {}".format(ctx.path_to_ss))
    ctx.admin_path = path.join(ctx.path_to_ss, Paths.ADMIN)
    server_txt = path.join(ctx.admin_path, Paths.SERVER)
    history_txt = path.join(ctx.admin_path, Paths.HISTORY)
    # lastid_txt = path.join(ctx.admin_path, Paths.LAST_TID)
    if not path.isfile(server_txt):
        print("Error: Wrong DB. Can't open server.txt")
        return
    if not path.isfile(history_txt):
        print("Error: Wrong DB. Can't open history.txt")
        return

    server = []
    with open(server_txt, 'r') as file_history:
        for cnt, line in enumerate(file_history):
            server.append(Transaction(line, ctx))

    print("Total transaction in server: {}".format(len(server)))
    last_transaction = server[len(server) - 1].tid
    print("Last transaction: {}".format(last_transaction))
    for transaction in server:
        if transaction.type == 'add':
            if not transaction.exists():
                print "Transaction {:010d} defected. Need remove from server.txt".format(transaction.tid)
                continue
            for file in transaction.files():
                if not file.exists():
                    print "Transaction {:010d} defected. A lack of flies. Need delete".format(transaction.tid)
                    break
            else:
                print "Transaction {:010d} is good.".format(transaction.tid)


if __name__ == '__main__':
    main()
