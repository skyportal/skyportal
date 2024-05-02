import datetime
import os
import tornado.web
from baselayer.app.access import permissions
from baselayer.log import make_log
from skyportal.utils.files import filesize_to_human_readable
from ...base import BaseHandler


log = make_log('js')


class LogHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self, file_name=None):
        """Log a frontend error to the server logs, tracking user crash reports."""
        data = self.get_json()
        log(f"{data['error']}{data['stack']}")
        return self.success()

    @permissions(["System admin"])
    def get(self, file_name=None):
        """Retrieve the contents of a log file, or list all log files (with human readable size and last_modified) if no file name is provided."""
        if file_name is None:
            # 1. grab the list of file names from the log directory, found in skyportal/log
            # 2. remove those that don't end in .log
            # 3. sort the files alphabetically
            # 4. format the output as a list of dictionaries, with each entry
            #    containing the file name, file size, and last modified time
            try:
                log_files = os.listdir('log')
                log_files = [f for f in log_files if f.endswith('.log')]
                log_files.sort()
                log_files = [
                    {
                        'name': f,
                        'size': filesize_to_human_readable(os.path.getsize(f'log/{f}')),
                        'last_modified': datetime.datetime.fromtimestamp(
                            os.path.getmtime(f'log/{f}')
                        ).strftime('%Y-%m-%d %H:%M:%S.%f'),
                    }
                    for f in log_files
                ]
                return self.success(data=log_files)
            except Exception as e:
                return self.error(f'Error reading log directory: {e}')
        else:
            # first verify that the log file exists
            if not os.path.exists(f'log/{file_name}'):
                return self.error(f'Log file {file_name} not found')

            log_data = ''
            try:
                with open(f'log/{file_name}') as f:
                    log_data = f.read()
            except Exception as e:
                return self.error(f'Error reading log file: {e}')

            # trigger a download of the .log file
            self.set_header('Content-Type', 'application/octet-stream')
            self.set_header('Content-Disposition', f'attachment; filename={file_name}')
            self.write(log_data)
