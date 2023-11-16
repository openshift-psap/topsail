from .__info__ import version


class Get_Info:
    """
    Command for retreiving information about the current topsail
    """

    def __new__(self):
        print('topsail version: ' + str(version))
