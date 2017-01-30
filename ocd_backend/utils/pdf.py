import tempfile
from urllib2 import HTTPError
from OpenSSL.SSL import ZeroReturnError

import pdfparser.poppler as pdf


def pdfparser(fname, pages=None):
    text_array = []
    try:
        d = pdf.Document(fname)
        for i, p in enumerate(d, start=1):
            for f in p:
                for b in f:
                    for l in b:
                        text_array.append(l.text.encode('UTF-8'))

            if i == 20:  # break after 20 pages
                break

        print "Processed %i pages" % (i)
        return '\n'.join(text_array)

    except Exception as e:
        print "Pdfparser Exception: ", e


class PDFToTextMixin(object):
    """
    Interface for converting a PDF file into text format using pdftotext
    """

    def pdf_clean_text(self, text):
        return text
        # return re.sub(r'\s+', u' ', text)

    def pdf_get_contents(self, url, max_pages=20):
        """
        Convenience method to download a PDF file and converting it to text.
        """
        tf = self.pdf_download(url)
        if tf is not None:
            return self.pdf_to_text(tf.name, max_pages)
        else:
            return u'' # FIXME: should be something else ...

    def pdf_download(self, url):
        """
        Downloads a given url to a tempfile.
        """

        print "Downloading %s" % (url,)
        try:
            # GO has no wildcard domain for SSL
            r = self.http_session.get(url, verify=False)
            tf = tempfile.NamedTemporaryFile()
            tf.write(r.content)
            tf.seek(0)
            return tf
        except HTTPError as e:
            print "Something went wrong downloading %s" % (url,)
        except ZeroReturnError as e:
            print "SSL Zero return error %s" % (url,)
        except Exception as e:
            print "Some other exception %s" % (url,)

    def pdf_to_text(self, path, max_pages=20):
        """
        Method to convert a given PDF file into text file using a subprocess
        """

        if max_pages > 0:
            content = pdfparser(path, range(0, max_pages))
        else:
            content = pdfparser(path)

        return unicode(self.pdf_clean_text(content.decode('utf-8')))
