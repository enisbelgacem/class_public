"""
.. module:: CPU
    :synopsis: CPU, a CLASS Plotting Utility
.. moduleauthor:: Benjamin Audren <benj_audren@yahoo.fr>
.. version:: 2.0

This is a small python program aimed to gain time when comparing two spectra,
i.e. from CAMB and CLASS, or a non-linear spectrum to a linear one.  It is
designed to be used in a command line fashion, not being restricted to your
CLASS directory, though it recognized mainly CLASS output format.  Far from
perfect, or complete, it could use any suggestion for enhancing it, just to
avoid losing time on useless matters for others.  Be warned that, when
comparing with other format, the following is assumed: there are no empty line
(especially at the end of file). Gnuplot comment lines (starting with a # are
allowed). This issue will cause a non-very descriptive error in CPU, any
suggestion for testing it is welcome.  Example of use: To superimpose two
different spectra and see their global shape :
python CPU.py output/lcdm_z2_pk.dat output/lncdm_z2_pk.dat
To see in details their ratio:
python CPU.py output/lcdm_z2_pk.dat output/lncdm_z2_pk.dat -r

"""
import numpy as np
import os
import matplotlib.pyplot as plt
import sys
import argparse
import itertools

START_LINE = {}
START_LINE['error'] = [r' /|\   ',
                       r'/_o_\  ',
                       r'       ']
START_LINE['warning'] = [r' /!\ ',
                         r'     ']
START_LINE['info'] = [r' /!\ ',
                      r'     ']

STANDARD_LENGTH = 80  # standard, increase if you have a big screen


def create_parser():
    parser = argparse.ArgumentParser(
        description=(
            'CPU, a CLASS Plotting Utility, specify wether you want\n'
            'to superimpose, or plot the ratio of different files.'),
        epilog=(
            'A standard usage would be, for instance:\n'
            'python CPU.py output/test_pk.dat output/test_pk_nl_density.dat'
            ' -r\npython CPU.py output/wmap_cl.dat output/planck_cl.dat'),
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument(
        'files', type=str, nargs='*', help='Files to plot')
    parser.add_argument('-r', '--ratio', dest='ratio', action='store_true',
                        help='Plot the ratio of the spectra')
    parser.add_argument('-s', '--selection', dest='selection',
                        nargs='+',
                        help='specify the fields you want to plot.')
    parser.add_argument('--scale', choices=['lin', 'loglog', 'loglin'],
                        type=str,
                        help='Specify the scale to use for the plot')
    parser.add_argument(
        '-p, --print',
        dest='printfile', action='store_true', default=False,
        help='print the graph directly in a .png file')
    parser.add_argument(
        '-r, --repeat',
        dest='repeat', action='store_true', default=False,
        help='repeat the step for all redshifts with same base name')
    return parser


def plot_CLASS_output(files, selection, ratio=False, output_name='',
                      extension='', x_variable='', scale='lin'):
    """
    Load the data to numpy arrays, write a Python script and plot them.

    Inspired heavily by the matlab version by Thomas Tram

    Parameters
    ----------
    files : list
        List of files to plot
    selection : list, or string
        List of items to plot, which should match the way they appear in the
        file, for instance: ['TT', 'BB]

    Keyword Arguments
    -----------------
    ratio : bool
        If set to yes, plots the ratio of the files, taking as a reference the
        first one
    output_name : str
        Specify a different name for the produced figure (by default, it takes
        the name of the first file, and replace the .dat by .pdf)
    extension : str


    """
    # Load all the graphs
    data = []
    for data_file in files:
        data.append(np.loadtxt(data_file))

    # Create the python script, and initialise it
    python_script_path = files[0]+'.py'
    text = '''
import matplotlib.pyplot as plt
import numpy as np\n'''

    # Create the full_path_files list, that contains the absolute path, so that
    # the future python script can import them directly.
    full_path_files = [os.path.abspath(elem) for elem in files]

    # Recover the base name of the files, everything before the .
    roots = [elem.split(os.path.sep)[-1].split('.')[0] for elem in files]

    text += '''files = %s\n''' % full_path_files
    text += '''
data = []
for data_file in files:
    data.append(np.loadtxt(data_file))\n'''

    # Recover the number of columns in the first file, as well as their title.
    num_columns, names, tex_names = extract_headers(files[0])

    # Check if everything is in order
    if num_columns == 2:
        selection = [names[1]]
    elif num_columns > 2:
        # in case selection was only a string, cast it to a list
        if isinstance(selection, str):
            selection = [selection]
        for elem in selection:
            if elem not in names:
                raise InputError(
                    "The entry 'selection' must contain names of the fields "
                    "in the specified files. You asked for %s " % elem +
                    "where I only found %s." % names)
    # Store the selected text and tex_names to the script
    text += 'selection = %s\n' % selection
    text += 'tex_names = %s\n' % [elem for (elem, name) in
                                  zip(tex_names, names) if name in selection]

    # Create the figure and ax objects
    fig, ax = plt.subplots()
    text += '\nfig, ax = plt.subplots()\n'

    # if ratio is not set, then simply plot them all
    if not ratio:
        text += 'for curve in data:\n'
        for idx, curve in enumerate(data):
            _, curve_names, _ = extract_headers(files[idx])
            for selec in selection:
                index = curve_names.index(selec)
                text += '    ax.'
                if scale == 'lin':
                    text += 'plot(curve[:, 0], curve[:, %i])\n' % index
                    ax.plot(curve[:, 0], curve[:, index])
                elif scale == 'loglog':
                    text += 'loglog(curve[:, 0], curve[:, %i])\n' % index
                    ax.loglog(curve[:, 0], curve[:, index])
        ax.legend([root+': '+elem for (root, elem) in
                   itertools.product(roots, selection)], loc='lower right')
        #ax.legend([
    else:
        ref = data[0]
        #for index in range(1, len(data)):
            #current = data[index]
            #if np.allclose(current[0], ref[0]):
                #ax.plot(current[0], current[colnum]/ref[colnum])
    text += 'plt.show()\n'
    plt.show()

    # Write to the python file all the issued commands. You can then reproduce
    # the plot by running "python output/something_cl.dat.py"
    with open(python_script_path, 'w') as python_script:
        python_script.write(text)


class FormatError(Exception):
    """Format not recognised"""
    pass


class TypeError(Exception):
    """Spectrum type not recognised"""
    pass


class NumberOfFilesError(Exception):
    """Invalid number of files"""
    pass


class InputError(Exception):
    """Incompatible input requirements"""
    pass


def replace_scale(string):
    """
    This assumes that the string starts with "(.)", which will be replaced by
    (8piG/3)

    >>> print replace_scale('(.)toto')
    >>> '(8\\pi G/3)toto'
    """
    string_list = list(string)
    string_list.pop(1)
    string_list[1:1] = list('8\\pi G/3')
    return ''.join(string_list)


def process_long_names(long_names):
    """
    Given the names extracted from the header, return two arrays, one with the
    short version, and one tex version

    >>> names, tex_names = process_long_names(['(.)toto', 'proper time [Gyr]'])
    >>> print names
    >>> ['toto', 'proper time']
    >>> print tex_names
    >>> ['(8\\pi G/3)toto, 'proper time [Gyr]']

    """
    names = []
    tex_names = []
    # First pass, to remove the leading scales
    for name in long_names:
        # This can happen in the background file
        if name.startswith('(.)', 0):
            temp_name = name[3:]
            names.append(temp_name)
            tex_names.append(replace_scale(name))
        # Otherwise, we simply
        else:
            names.append(name)
            tex_names.append(name)
    # Second pass, to remove from the short names the indication of scale,
    # which should look like something between parenthesis, or square brackets,
    # and located at the end of the string
    for index, name in enumerate(names):
        if name.find('(') != -1:
            names[index] = name[:name.index('(')]
        elif name.find('[') != -1:
            names[index] = name[:name.index('[')]

    return names, tex_names


def extract_headers(header_path):
    with open(header_path, 'r') as header_file:
        header = [line for line in header_file if line[0] == '#']
        header = header[-1]

    # Count the number of columns in the file, and recover their name. Thanks
    # Thomas Tram for the trick
    indices = [i+1 for i in range(len(header)) if
               header.startswith(':', i)]
    num_columns = len(indices)
    long_names = [header[indices[i]:indices[(i+1)]-3].strip() if i < num_columns-1
                  else header[indices[i]:].strip()
                  for i in range(num_columns)]

    # Process long_names further to handle special cases, and extract names,
    # which will correspond to the tags specified in "selection".
    names, tex_names = process_long_names(long_names)

    return num_columns, names, tex_names


def main():
    print '~~~ Running CPU, a CLASS Plotting Utility ~~~'
    parser = create_parser()
    # Parse the command line arguments
    args = parser.parse_args()

    # if there are no argument in the input, print usage
    if len(args.files) == 0:
        parser.print_usage()
        return

    # Ratio is not implemented yet, catch it
    if args.ratio:
        raise InputError(
            "Sorry, this is not working yet")
    # if the first file name contains cl or pk, infer the type of desired
    # spectrum
    if not args.selection:
        if args.files[0].rfind('cl') != -1:
            selection = 'TT'
            scale = 'loglog'
        elif args.files[0].rfind('pk') != -1:
            selection = 'P'
            scale = 'loglog'
        else:
            raise TypeError(
                "Please specify a field to plot")
        args.selection = selection
    else:
        scale = ''
    if not args.scale:
        if scale:
            args.scale = scale
        else:
            args.scale = 'lin'

    # If ratio is asked, but only one file was passed in argument, politely
    # complain
    if args.ratio:
        if len(args.files) < 2:
            raise NumberOfFilesError(
                "If you want me to compute a ratio between two files, "
                "I strongly encourage you to give me at least two of them.")
    # actual plotting. By default, a simple superposition of the graph is
    # performed. If asked to be divided, the ratio is shown - whether a need
    # for interpolation arises or not.
    plot_CLASS_output(args.files, args.selection,
                      ratio=args.ratio, scale=args.scale)

if __name__ == '__main__':
    sys.exit(main())
