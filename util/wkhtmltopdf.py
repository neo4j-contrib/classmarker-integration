import os
from subprocess import Popen
from subprocess import PIPE

class WKhtmlToPdf(object):
    """
    Convert an html page via its URL into a pdf.
    """

    def __init__(self, *args, **kwargs):
        self.url = None
        self.output_file = None

        # get the url and output_file options
        try:
            self.url, self.output_file = args[0], args[1]
        except IndexError:
            pass

        if not self.url or not self.output_file:
            raise Exception("Missing url and output file arguments")

        # save the file to /tmp if a full path is not specified
        output_path = os.path.split(self.output_file)[0]
        if not output_path:
            self.output_file = os.path.join('/tmp', self.output_file)

        self.params = []
        self.screen_resolution = [1024, 768]
        self.color_depth = 24

    def render(self):
        """
        Render the URL into a pdf and setup the evironment if required.
        """

        # execute the command
        command = './binary/wkhtmltopdf -O Landscape %s "%s" "%s" >> /tmp/wkhtp.log' % (
            " ".join([cmd for cmd in self.params]),
            self.url,
            self.output_file
        )
        try:
            p = Popen(command, shell=True,
                      stdout=PIPE, stderr=PIPE, close_fds=True)
            stdout, stderr = p.communicate()
            retcode = p.returncode

            if retcode == 0:
                # call was successful
                return
            elif retcode < 0:
                raise Exception("terminated by signal: ", -retcode)
            else:
                raise Exception(stderr)

        except OSError as exc:
            raise exc


def wkhtmltopdf(*args, **kwargs):
    wkhp = WKhtmlToPdf(*args, **kwargs)
    wkhp.render()
