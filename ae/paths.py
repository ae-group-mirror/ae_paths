"""
generic file path helpers
=========================

this pure python namespace portion is providing generic file paths together with useful helper functions and classes
that are independent from the operating system. the currently support operating systems are:

    * android OS
    * iOS
    * linux
    * MacOS
    * Windows

the classes :class:`Collector` and :class:`FilesRegister` collect and group available files. :class:`Collector` is more
for temporary quick searches, while the class :class:`FilesRegister` is used to permanent registers in which you later
can find the best fitting match for a requested purpose - useful for dynamic selection of image/font/audio/... resource
files that have to be selected depending on the current user preferences, hardware and/or software environment.

this portion is also encapsulating helper functions from Python's :mod:`shutil` module as aliases (see
:func:`copy_file`, :func:`copy_tree`, :func:`move_file` and :func:`move_tree`).

the only external hard dependency of this module are the ae namespace portions :mod:`ae.base` and :mod:`ae.files`.
optional dependencies are:

    * on android OS the PyPi package `jnius`, needed by the functions :func:`user_data_path` and :func:`user_docs_path`.
    * the `plyer` PyPi package, needed by the function :func:`add_common_storage_paths`.


generic system paths
--------------------

some generic system paths are determined by the following helper functions:

* :func:`app_data_path`: application data path.
* :func:`app_docs_path`: application documents path.
* :func:`user_data_path`: user data path.
* :func:`user_docs_path`: user documents path.

these system paths together with additional generic paths like e.g. the current working directory, as well as file path
parts (like e.g. the user or application name) are provided as `path placeholders`, which are stored within the
:data:`PATH_PLACEHOLDERS` dict.

the helper function :func:`norm_path` converts path strings containing path placeholders into regular path strings.
:func:`path_name` and :func:`placeholder_paths` are converting regular path strings or parts of it into path
placeholders.

by calling the function :func:`add_common_storage_paths` all storage paths provided by the `plyer` package will be
added to the path placeholders (the :data:`PATH_PLACEHOLDERS` dict).


path helper functions
---------------------

the function :func:`move_tree` is moving entire directory trees (including their files and sub-folders), whereas
:func:`move_files` are only moving the files from a directory tree to another location.

with :func:`path_files` you can easily determine the files within a folder structure that are matching the specified
wildcards and path part placeholders (provided by :data:`PATH_PLACEHOLDERS`).


file/folder collection and classification
-----------------------------------------

more specific path examinations on the files and sub-folders of a file path can be done with the :class:`Collector`
and :class:`FilesRegister` classes.


collecting files
^^^^^^^^^^^^^^^^

:class:`Collector` is scanning multiple paths for file names. the following example is using :class:`Collector` to
collect the files with the name `xxx.cfg` in the current working directory, in the folder above the application data
folder, and in a folder with the name of the main application underneath the user data folder::

    coll = Collector()
    coll.collect("{cwd}", "{app}/..", "{usr}/{main_app_name}", append="xxx" + CFG_EXT)
    found_files = coll.files

to add or overwrite the generic path placeholder parts values of the main application name (`{main_app_name}`) and
the application data path (`{app}`) you simply specify them in the construction of the :class:`Collector` instance::

    coll = Collector(main_app_name=..., app=...)

additionally you can specify any other path placeholders that will be automatically used and replaced by the
:class:`Collector` instance::

    coll = Collector(any_other_placeholder=...)

all found files are provided by the :attr:`Collector.files` instance attribute. found folders will be separately
collected within the :class:`Collector` instance attribute :attr:`~Collector.paths`.

by default only the found file(s)/folder(s) of the first combination will be collected. to collect all files instead,
pass an empty tuple to the :meth:`~Collector.collect' method argument :paramref:`~Collector.collect.only_first_of`::

    coll.collect(..., only_first_of=())

add one of the strings `'prefix'`, `'append'` or `'select'` to the :paramref:`~Collector.collect.only_first_of` tuple
argument to collect only the files/folders of the first combination of the specified prefixes, append-suffixes
and select-suffixes.

the following example determines all folders underneath the current working directory with a name that contains the
string `'xxx'` or is starting with `'yyy'` or is ending with  `'zzz'`::

    coll = Collector()
    coll.collect('{cwd}', append=('*xxx*', 'yyy*', '*zzz'))
    folders = coll.paths

by using the :paramref:`~Collector.collect.select` argument the found files and folders will additionally be collected
in the :class:`Collector` instance attribute :attr:`~Collector.selected`.

the combinations compiled via the :paramref:`~Collector.collect.select` argument that are not existing will be counted.
the results are provided by the instance attributes :attr:`~Collector.failed`, :attr:`~Collector.prefix_failed` and
:attr:`~Collector.suffix_failed`.

the :paramref:`~Collector.collect.select` argument can also be passed together with the
:paramref:`~Collector.collect.append` argument.

multiple calls of :meth:`~Collector.collect` are accumulating found files and folders to the respective instance
attributes::

    coll = Collector()
    coll.collect(...)
    coll.collect(...)
    ...
    files = coll.files
    folders = coll.paths
    items = coll.selected


files register
^^^^^^^^^^^^^^

a files register is an instance of the :class:`FilesRegister`, providing property based file collection and selection,
which is e.g. used by the :mod:`ae.gui_app` ae namespace portion to find and select resource files like icon/image or
sound files.

files can be collected from various places by a single instance of the class :class:`FilesRegister`::

    from ae.files import FilesRegister

    fr = FilesRegister('first/path/to/collect')
    fr.add_paths('second/path/to/collect/files/from')

    registered_file = fr.find_file('file_name')

in this example the :class:`FilesRegister` instance collects all files that are existing in any sub-folders underneath
the two provided paths. then the :meth:`~FilesRegister.find_file` method will return a file object of type
:class:`~ae.files.RegisteredFile` of the last found file with the base name (or stem) `file_name`.

several files with the same base name can be collected and registered e.g. with different formats, to be selected by
the app by their different properties. assuming your application is providing an icon image in two sizes, provided
within the following directory structure::

    resources/
        size_72/
            app_icon.jpg
        size_150/
            app_icon.png

first create an instance of :class:`FilesRegister` to collect both image files from the `resources` folder::

    fr = FilesRegister('resources')

the resulting object `fr` behaves like a dict object, where the item key is the file base name without extension
('app_icon') and the item value is a list of instances of :class:`~ae.files.RegisteredFile`. both files in the
resources folder are provided as one dict item::

    assert 'app_icon' in fr
    assert len(fr) == 1
    assert len(fr['app_icon']) == 2
    assert isinstance(fr['app_icon'][0], RegisteredFile)

to select the appropriate image file you can use the :meth:`~FilesRegister.find_file` method::

    app_icon_image_path = fr.find_file('app_icon', dict(size=current_size))

as a shortcut you can alternatively call the object directly (leaving `.find_file` away)::

    app_icon_image_path = fr('app_icon', dict(size=current_size))

if the `current_size` variable contains the integer ``150``, then `app_icon_image_path` will result in
`"resources/size_150/app_icon.png"`. in contrary if the `current_size` variable contains the integer `72`, then
`app_icon_image_path` will result in `"resources/size_72/app_icon.png"`.

for more complex selections you can use callables passed into the :paramref:`~FilesRegister.find_file.property_matcher`
and :paramref:`~FilesRegister.find_file.file_sorter` arguments of :meth:`~FilesRegister.find_file`.
"""
import glob
import os
import shutil
import string
import sys
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

from ae.base import app_name_guess, env_str, os_platform                        # type: ignore
from ae.files import CachedFile, FileObject, PropertiesType, RegisteredFile     # type: ignore


__version__ = '0.2.19'


APPEND_TO_END_OF_FILE_LIST = sys.maxsize
""" special flag default value for the `first_index` argument of the `add_*` methods of :class:`FilesRegister` to
    append new file objects to the end of the name's register file object list.
"""
INSERT_AT_BEGIN_OF_FILE_LIST = -APPEND_TO_END_OF_FILE_LIST
""" special flag default value for the `first_index` argument of the `add_*` methods of :class:`FilesRegister` to
    insert new file objects always at the begin of the name's register file object list.
"""


def add_common_storage_paths():
    """ add common storage paths to :data:`PATH_PLACEHOLDERS` depending on the operating system (OS).

    the following storage paths are provided by the `plyer` PyPi package (not all of them are available in each OS):

    * `application`: user application directory.
    * `documents`: user documents directory.
    * `downloads`: user downloads directory.
    * `external_storage`: external storage root directory.
    * `home`: user home directory.
    * `music`: user music directory.
    * `pictures`: user pictures directory.
    * `root`: root directory of the operating system partition.
    * `sdcard`: SD card root directory.
    * `videos`: user videos directory.

    additionally storage paths that are only available on certain OS (inspired by the method `get_drives`, implemented
    in `<https://github.com/kivy-garden/filebrowser/blob/master/kivy_garden/filebrowser/__init__.py>`_):

    * `Linux`: external storage devices/media mounted underneath the system partition root in /mnt or /media.
    * `Apple Mac OsX or iOS`: external storage devices/media mounted underneath the system partition root in /Volume.
    * `MS Windows`: additional drives mapped as the drive partition name.

    """
    from plyer import storagepath                              # type: ignore  # pylint: disable=import-outside-toplevel

    for attr in dir(storagepath):
        if attr.startswith('get_') and attr.endswith('_dir'):
            try:
                PATH_PLACEHOLDERS[attr[4:-4]] = getattr(storagepath, attr)()
            except (AttributeError, NotImplementedError, FileNotFoundError, Exception):
                pass

    if os_platform == 'linux':
        places = ('/mnt', '/media')
        for place in places:
            if os.path.isdir(place):
                for directory in next(os.walk(place))[1]:
                    PATH_PLACEHOLDERS[directory] = os.path.join(place, directory)

    elif os_platform in ('darwin', 'ios'):      # pragma: no cover
        vol = '/Volume'
        if os.path.isdir(vol):
            for drive in next(os.walk(vol))[1]:
                PATH_PLACEHOLDERS[drive] = os.path.join(vol, drive)

    elif os_platform in ('win32', 'cygwin'):    # pragma: no cover
        from ctypes import windll, create_unicode_buffer

        bitmask = windll.kernel32.GetLogicalDrives()
        get_volume_information = windll.kernel32.GetVolumeInformationW
        for letter in string.ascii_uppercase:
            drive = letter + ':' + os.path.sep
            if bitmask & 1 and os.path.isdir(drive):
                buf_len = 64
                name = create_unicode_buffer(buf_len)
                get_volume_information(drive, name, buf_len, None, None, None, None, 0)
                PATH_PLACEHOLDERS[name.value] = drive
            bitmask >>= 1


def app_data_path() -> str:
    """ determine the os-specific absolute path of the {app} directory where user app data can be stored.

    .. hint:: use :func:`app_docs_path` instead to get a more public path to the user.

    :return:                    path string of the user app data folder.
    """
    return os.path.join(user_data_path(), PATH_PLACEHOLDERS.get('main_app_name', PATH_PLACEHOLDERS['app_name']))


def app_docs_path() -> str:
    """ determine the os-specific absolute path of the {ado} directory where user documents app are stored.

    .. hint:: use :func:`app_data_path` instead to get a more hidden path to the user.

    :return:                    path string of the user documents app folder.
    """
    return os.path.join(user_docs_path(), PATH_PLACEHOLDERS.get('main_app_name', PATH_PLACEHOLDERS['app_name']))


copy_file = shutil.copy2
""" alias for :func:`shutil.copy2` (compatible to :func:`shutil.copy`, :func:`shutil.copyfile` and
:func:`ae.files.copy_bytes`. """


copy_tree = shutil.copytree
""" alias for :func:`shutil.copytree`. """


move_file = shutil.move
""" alias for :func:`shutil.move` (see also :func:`~ae.paths.move_tree`). """


def move_files(src_folder: str, dst_folder: str, overwrite: bool = False) -> List[str]:
    """ move files from src_folder into optionally created dst_folder, optionally overwriting destination files.

    :param src_folder:          path to source folder/directory where the files get moved from. placeholders in
                                :data:`PATH_PLACEHOLDERS` will be recognized and substituted.
                                please note that the source folders itself will neither be moved nor removed (but will
                                be empty after the operation finished).
    :param dst_folder:          path to destination folder/directory where the files get moved to. all placeholders in
                                :data:`PATH_PLACEHOLDERS` are recognized and will be substituted.
    :param overwrite:           pass True to overwrite existing files in the destination folder/directory. on False the
                                files will only get moved if they not exist in the destination.
    :return:                    list of moved files, with their destination path.
    """
    src_folder = norm_path(src_folder)
    dst_folder = norm_path(dst_folder)

    updated = list()

    if os.path.exists(src_folder):
        for src_file in glob.glob(os.path.join(src_folder, '**'), recursive=True):
            if os.path.isfile(src_file):
                dst_file = os.path.abspath(os.path.join(dst_folder, os.path.relpath(src_file, src_folder)))
                if overwrite or not os.path.exists(dst_file):
                    dst_sub_dir = os.path.dirname(dst_file)
                    if not os.path.exists(dst_sub_dir):
                        os.makedirs(dst_sub_dir)
                    updated.append(move_file(src_file, dst_file))

    return updated


move_tree = shutil.move
""" another alias for :func:`shutil.move` (see also :func:`~ae.paths.move_file`). """


def norm_path(path: str) -> str:
    """ normalize/transform path replacing `PATH_PLACEHOLDERS` and the tilde character (for home folder).

    :param path:                path string to normalize/transform.
    :return:                    normalized path string.
    """
    path = path.format(**PATH_PLACEHOLDERS)
    if path[0:1] == "~":
        path = os.path.expanduser(path)
    return path


def path_files(file_mask: str, recursive: bool = True,
               # file_class: Union[Type[Any], Callable[[str, KwArg()], Any]] = str, **file_kwargs) -> List[Any]:
               file_class: Union[Type[Any], Callable] = str, **file_kwargs) -> List[Any]:
    """ determine existing file(s) underneath the folder specified by :paramref:`~path_files.path`.

    :param file_mask:           glob file mask (with optional glob wildcards and :data:`PATH_PLACEHOLDERS`)
                                specifying the files to collect (by default including the sub-folders).
    :param recursive:           pass False to only collect the given folder (ignoring sub-folders).
    :param file_class:          factory used for the returned list items (see :paramref:`path_items.creator`).
    :param file_kwargs:         additional/optional kwargs apart from file name passed onto the used item_class.
    :return:                    list of files of the class specified by :paramref:`~path_files.item_class`.
    """
    return path_items(file_mask, recursive=recursive, selector=os.path.isfile, creator=file_class, **file_kwargs)


def path_folders(folder_mask: str, recursive: bool = True,
                 # folder_class: Union[Type[Any], Callable[[str, KwArg()], Any]] = str, **folder_kwargs) -> List[Any]:
                 folder_class: Union[Type[Any], Callable] = str, **folder_kwargs) -> List[Any]:
    """ determine existing folder(s) underneath the folder specified by :paramref:`~path_folders.path`.

    :param folder_mask:         glob folder mask (with optional glob wildcards and :data:`PATH_PLACEHOLDERS`)
                                specifying the folders to collect (by default including the sub-folders).
    :param recursive:           pass False to only collect the given folder (ignoring sub-folders).
    :param folder_class:        class or factory used for the returned list items (see :paramref:`~path_items.creator`).
    :param folder_kwargs:       additional/optional kwargs apart from file name passed onto the used item_class.
    :return:                    list of folders of the class specified by :paramref:`~path_folders.item_class`.
    """
    return path_items(folder_mask, recursive=recursive, selector=os.path.isdir, creator=folder_class, **folder_kwargs)


def path_items(item_mask: str, recursive: bool = True, selector: Callable[[str], bool] = os.path.exists,
               # creator: Union[Type[Any], Callable[[str, KwArg()], Any]] = str, **creator_kwargs) -> List[Any]:
               creator: Union[Type[Any], Callable] = str, **creator_kwargs) -> List[Any]:
    """ determine existing file/folder item(s) underneath the folder specified by :paramref:`~path_items.path`.

    :param item_mask:           file path mask (with optional glob wildcards and :data:`PATH_PLACEHOLDERS`)
                                specifying the files/folders to collect (by default including the sub-folders).
    :param recursive:           pass False to only collect within the specified folder (ignoring sub-folders).
    :param selector:            called with each found file/folder name to check if it has to be added
                                to the returned list.
    :param creator:             each found file/folder will be passed as argument to this class/callable and the
                                instance/return-value will be appended as an item to the returned item list.
                                if not passed then the `str` class will be used, which means that the items
                                of the returned list will be strings of the file/folder path and name.
                                if a class, like e.g. :class:`ae.files.CachedFile`, :class:`ae.files.CachedFile`
                                or :class:`pathlib.Path`, get passed then the items will be instances of this class.
                                alternatively you can pass a callable which will be called on each found file/folder.
                                in this case the return value of the callable will be inserted in the related
                                item of the returned list.
    :param creator_kwargs:      additional/optional kwargs passed onto the used item_class apart from the item name.
    :return:                    list of found and selected items of the item class (:paramref:`~path_items.item_class`).
    """
    item_mask = norm_path(item_mask)
    # if recursive and '*' not in item_mask and '?' not in item_mask:
    #    item_mask = os.path.join(item_mask, '**')

    items = list()
    for part in glob.glob(item_mask, recursive=recursive):
        if selector(part):
            items.append(creator(part, **creator_kwargs))

    return items


def path_name(path: str) -> str:
    """ determine placeholder key name of the specified path.

    :param path:                path string to determine name of (can contain placeholders).
    :return:                    name (respectively dict key in :data:`PATH_PLACEHOLDERS`) of the found path
                                or empty string if not found.
    """
    search_path = norm_path(path)
    for name, registered_path in PATH_PLACEHOLDERS.items():
        if norm_path(registered_path) == search_path:
            return name
    return ""


def placeholder_key(path: str) -> str:
    """ determine :data:`PATH_PLACEHOLDERS` key of specified path.

    :param path:                path string starting with a :data:`PATH_PLACEHOLDERS` path prefix.
    :return:                    placeholder key (if found as path prefix), else empty string.
    """
    ph_path = placeholder_path(path)
    if ph_path[0] == '{':
        idx = ph_path.find('}')
        if idx != -1:
            return ph_path[1:idx]
    return ""


def placeholder_path(path: str) -> str:
    """ replace begin of path string with the longest prefix found in :data:`PATH_PLACEHOLDERS`.

    :param path:                path string (optionally including sub-folders and file name).
    :return:                    path string with replaced placeholder prefix (if found).
    """
    for key in sorted(PATH_PLACEHOLDERS, key=lambda k: len(PATH_PLACEHOLDERS[k]), reverse=True):
        val = PATH_PLACEHOLDERS[key]
        if path.startswith(val):
            return "{" + key + "}" + path[len(val):]
    return path


def series_file_name(file_path: str, digits: int = 2, marker: str = " ", create: bool = False) -> str:
    """ determine non-existent series file name with an unique series index.

    :param file_path:           file path and name (optional with extension).
    :param digits:              number of digits used for the series index.
    :param marker:              marker that will be put at the end of the file name and before the series index.
    :param create:              pass True to create the file (to reserve the series index).
    :return:                    file path extended with unique/new series index.
    """
    path_stem, ext = os.path.splitext(file_path)
    path_stem += marker

    found_files = glob.glob(path_stem + "*" + ext)
    index = len(found_files) + 1
    while True:
        file_path = path_stem + format(index, "0" + str(digits)) + ext
        if not os.path.exists(file_path):
            break
        index += 1

    if create:
        open(file_path, 'w').close()

    return file_path


def user_data_path() -> str:
    """ determine the os-specific absolute path of the {usr} directory where user data can be stored.

    .. hint::
        this path is not accessible on Android devices, use :func:`user_docs_path` instead to get a more public
        path to the user.

    :return:    path string of the user data folder.
    """
    if os_platform == 'android':            # pragma: no cover
        from jnius import autoclass, cast   # type: ignore  # pylint: disable=no-name-in-module, import-outside-toplevel
        # noinspection PyPep8Naming
        PythonActivity = autoclass('org.kivy.android.PythonActivity')   # pylint: disable=invalid-name
        context = cast('android.content.Context', PythonActivity.mActivity)
        file_p = cast('java.io.File', context.getFilesDir())
        data_path = file_p.getAbsolutePath()

    elif os_platform in ('win32', 'cygwin'):
        data_path = env_str('APPDATA')

    else:
        if os_platform == 'ios':
            data_path = 'Documents'
        elif os_platform == 'darwin':
            data_path = os.path.join('Library', 'Application Support')
        else:                                       # platform == 'linux' or 'freebsd' or anything else
            data_path = env_str('XDG_CONFIG_HOME') or '.config'

        if not os.path.isabs(data_path):
            data_path = os.path.expanduser(os.path.join('~', data_path))

    return data_path


def user_docs_path() -> str:
    """ determine the os-specific absolute path of the {doc} directory where the user is storing the personal documents.

    .. hint:: use :func:`user_data_path` instead to get a more hidden user data.

    :return:                    path string of the user documents folder.
    """
    if os_platform == 'android':            # pragma: no cover
        from jnius import autoclass         # type: ignore  # pylint: disable=no-name-in-module, import-outside-toplevel
        # noinspection PyPep8Naming
        Environment = autoclass('android.os.Environment')  # pylint: disable=invalid-name
        docs_path = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOCUMENTS).getAbsolutePath()

    elif os_platform in ('win32', 'cygwin'):
        docs_path = os.path.join(env_str('USERPROFILE'), 'Documents')

    else:
        docs_path = os.path.expanduser(os.path.join('~', 'Documents'))

    return docs_path


PATH_PLACEHOLDERS = dict()   #: placeholders of user-, os- and app-specific system paths and file name parts

PATH_PLACEHOLDERS['app_name'] = app_name_guess()

PATH_PLACEHOLDERS['ado'] = app_docs_path()
PATH_PLACEHOLDERS['app'] = app_data_path()
PATH_PLACEHOLDERS['cwd'] = os.getcwd()
PATH_PLACEHOLDERS['doc'] = user_docs_path()
PATH_PLACEHOLDERS['usr'] = user_data_path()


class Collector:
    """ file/folder collector """
    def __init__(self, path_scanner: Callable[[str], Iterable] = path_files, **placeholders):
        """ create new file/folder/item collector instance with individual (extended or overriding) placeholders.

        :param path_scanner:    callable to determine the item type to collect. the default is the :func:`path_files`
                                function. pass e.g. :func:`path_folders` to collect only folders or :func:`path_items`
                                to collect both (files and folders).
        :param placeholders:    `format` kwargs where keys are the placeholders and the values the replacements. the
                                placeholders provided by :data:`PATH_PLACEHOLDERS` are available too (but will be
                                overwritten by these arguments).
        """
        self._path_scanner = path_scanner

        self.paths: List[str] = list()                  #: list of found/collected folder names
        self.files: List[str] = list()                  #: list of found/collected file names
        self.selected: List[str] = list()               #: list of found/collected file/folder item names
        self.failed = 0                                 #: number of not found select-combinations
        self.prefix_failed: Dict[str, int] = dict()     #: number of not found select-combinations for each prefix
        self.suffix_failed: Dict[str, int] = dict()     #: number of not found select-combinations for each suffix

        self.placeholders = PATH_PLACEHOLDERS.copy()    #: path part placeholders of this Collector instance
        self.placeholders.update(placeholders)

    def check_add(self, name: str, select: bool = False) -> bool:
        """ check if name file or folder and if yes append accordingly to instance lists else do nothing.

        :param name:            file/folder name, optionally including wildcards in the glob.glob format.
        :param select:          pass True to add found files/folders into :attr:`~Collector.selected`.
        :return:                True if at least one file/folder got found/added, else False.
        """
        added_any = False
        for file_path in self._path_scanner(name) if '*' in name or '?' in name else (name, ):
            found = True
            if os.path.isdir(file_path):
                self.paths.append(file_path)
                added_any = True
            elif os.path.isfile(file_path):
                self.files.append(file_path)
                added_any = True
            else:
                found = False
            if select and found:
                self.selected.append(file_path)
        return added_any

    def _collect_appends(self, prefix: str, appends: Tuple[str, ...], only_first_of: Tuple[str, ...]):
        for suffix in appends:
            name = os.path.join(prefix, suffix).format(**self.placeholders)
            if self.check_add(name) and 'append' in only_first_of:
                return

    def _collect_selects(self, prefix: str, selects: Tuple[str, ...], only_first_of: Tuple[str, ...]):
        if prefix not in self.prefix_failed:
            self.prefix_failed[prefix] = 0
        for suffix in selects:
            name = os.path.join(prefix, suffix).format(**self.placeholders)
            if not self.check_add(name, select=True):
                self.failed += 1
                self.prefix_failed[prefix] += 1
                if suffix not in self.suffix_failed:
                    self.suffix_failed[suffix] = 0
                self.suffix_failed[suffix] += 1
            elif 'select' in only_first_of:
                return

    def collect(self, *prefixes: str,
                append: Union[str, Tuple[str, ...]] = (), select: Union[str, Tuple[str, ...]] = (),
                only_first_of: Union[str, Tuple[str, ...]] = ('append', 'prefix', 'select', )):
        """ collect additional files/folders by combining the given prefixes with all the given append/select suffixes.

        :param prefixes:        tuple of file/folder paths to be used as prefix.
        :param append:          tuple of file/folder names to be used as append suffix.
        :param select:          tuple of file/folder names to be used as select suffix.
        :param only_first_of:   tuple with the strings `'prefix'`, `'append'` or `'select'` or one of these strings.
                                if it contains the string `'prefix'` then only the files/folders of the first
                                combination will be collected. if it contains `'append'` then only the files/folders of
                                the first combination done with the suffixes passed into the :paramref:`~collect.append`
                                argument will be collected. if it contains `'select'` then only the files/folders of the
                                first combination done with the suffixes passed into the :paramref:`~collect.select`
                                argument will be collected. pass empty tuple to collect all combinations.

        each of the passed :paramref:`~collect.prefixes` will be combined with the suffixes specified in
        :paramref:`~collect.append` and in :paramref:`~collect.select`. the resulting file/folder paths that are exist,
        will then be added to the appropriate instance attribute, either :attr:`~Collector.files` for a file or
        :attr:`~Collector.paths` for a folder.

        additionally the existing file/folder paths from the combinations of :paramref:`~collect.prefixes` and
        :paramref:`~collect.select` will be added in the :attr:`~Collector.selected` list attribute.

        all arguments of this method can either be passed either as tuples or as a single string value.

        .. hint:: more details and some examples are available in the doc string of this :mod:`module <ae.paths>`.
        """

        if not append and not select:
            select = ("", )
        else:
            if isinstance(append, str):
                append = (append, )
            if isinstance(select, str):
                select = (select, )
        if isinstance(only_first_of, str):
            only_first_of = (only_first_of, )

        for prefix in prefixes:
            prefix_count = len(self.paths) + len(self.files)
            self._collect_appends(prefix, append, only_first_of)    # type: ignore  # mypy is sometimes so silly?!?!?
            self._collect_selects(prefix, select, only_first_of)
            if 'prefix' in only_first_of and len(self.paths) + len(self.files) > prefix_count:
                break


class FilesRegister(dict):
    """ file register catalog - see also :ref:`files register` examples. """
    def __init__(self, *add_path_args,
                 property_matcher: Optional[Callable[[FileObject, ], bool]] = None,
                 file_sorter: Optional[Callable[[FileObject, ], Any]] = None,
                 **add_path_kwargs):
        """ create files register instance.

        this method gets redirected with :paramref:`~FilesRegister.add_path_args` and
        :paramref:`~FilesRegister.add_path_kwargs` arguments to :meth:`~FilesRegister.add_paths`.

        :param add_path_args:   if passed then :meth:`~FilesRegister.add_paths` will be called with this args tuple.
        :param property_matcher: property matcher callable, used as default value by :meth:`~FilesRegister.find_file` if
                                not passed there.
        :param file_sorter:     file sorter callable, used as default value by :meth:`~FilesRegister.find_file` if not
                                passed there.
        :param add_path_kwargs: passed onto call of :meth:`~FilesRegister.add_paths` if the
                                :paramref:`~FilesRegister.add_path_args` got provided by the caller.
        """
        super().__init__()
        self.property_watcher = property_matcher
        self.file_sorter = file_sorter
        if add_path_args:
            self.add_paths(*add_path_args, **add_path_kwargs)

    def __call__(self, *find_args, **find_kwargs) -> Optional[FileObject]:
        """ add_path_args and kwargs will be completely redirected to :meth:`~FilesRegister.find_file`. """
        return self.find_file(*find_args, **find_kwargs)

    def add_file(self, file_obj: FileObject, first_index: int = APPEND_TO_END_OF_FILE_LIST):
        """ add a single file to the list of this dict mapped by the file-name/stem as dict key.

        :param file_obj:        either file path string or any object with a `stem` attribute.
        :param first_index:     pass list index -n-1..n-1 to insert :paramref:`~add_file.file_obj` in the name's list.
                                values greater than n (==len(file_list)) will append the file_obj to the end of the file
                                object list and values less than n-1 will insert the file_obj to the begin.
        """
        name = os.path.splitext(os.path.basename(file_obj))[0] if isinstance(file_obj, str) else file_obj.stem
        if name in self:
            list_len = len(self[name])
            if first_index < 0:
                first_index = max(0, list_len + first_index + 1)
            else:
                first_index = min(first_index, list_len)
            self[name].insert(first_index, file_obj)
        else:
            self[name] = [file_obj]

    def add_files(self, files: Iterable[FileObject], first_index: int = APPEND_TO_END_OF_FILE_LIST) -> List[str]:
        """ add files from another :class:`FilesRegister` instance.

        :param files:           iterable with file objects to be added.
        :param first_index:     pass list index -n-1..n-1 to insert the first file_obj in each name's register list.
                                values greater than n (==len(file_list)) will append the file_obj to the end of the file
                                object list. the order of the added items will be unchanged if this value is greater or
                                equal to zero. negative values will add the items from :paramref:`~add_files.files` in
                                reversed order and **after** the item specified by this index value (so passing -1 will
                                append the items to the end in reversed order, while passing -(n+1) will insert them at
                                the begin in reversed order).
        :return:                list of paths of the added files.
        """
        increment = -1 if first_index < 0 else 1
        added_file_paths = list()
        for file_obj in files:
            self.add_file(file_obj, first_index=first_index)
            added_file_paths.append(str(file_obj))
            first_index += increment
        return added_file_paths

    def add_paths(self, *file_path_masks: str, recursive: bool = True, first_index: int = APPEND_TO_END_OF_FILE_LIST,
                  file_class: Type[FileObject] = RegisteredFile, **init_kwargs) -> List[str]:
        """ add files found in the folder(s) specified by the :paramref:`~add_paths.file_path_masks` args.

        :param file_path_masks: file path masks (with optional wildcards and :data:`~ae.paths.PATH_PLACEHOLDERS`)
                                specifying the files to collect (by default including the sub-folders).
        :param recursive:       pass False to only collect the given folder (ignoring sub-folders).
        :param first_index:     pass list index -n-1..n-1 to insert the first file_obj in each name's register list.
                                values greater than n (==len(file_list)) will append the file_obj to the end of the file
                                object list. the order of the added items will be unchanged if this value is greater
                                or equal to zero. negative values will add the found items in reversed
                                order and **after** the item specified by this index value (so passing -1 will append
                                the items to the end in reversed order, while passing -(n+1) will insert them at the
                                begin in reversed order).
        :param file_class:      the used file object class (see :data:`FileObject`). each found file object will passed
                                to the class constructor (callable) and added to the list which is a item of this dict.
        :param init_kwargs:     additional/optional kwargs passed onto the used :paramref:`~add_paths.file_class`. pass
                                e.g. the object_loader to use, if :paramref:`~add_paths.file_class` is
                                :class:`CachedFile` (instead of the default: :class:`RegisteredFile`).
        :return:                list of paths of the added files.
        """
        added_file_paths = list()
        for mask in file_path_masks:
            added_file_paths.extend(
                self.add_files(path_files(mask, recursive=recursive, file_class=file_class, **init_kwargs),
                               first_index=first_index))
        return added_file_paths

    def add_register(self, files_register: 'FilesRegister', first_index: int = APPEND_TO_END_OF_FILE_LIST) -> List[str]:
        """ add files from another :class:`FilesRegister` instance.

        :param files_register:  files register instance containing the file_obj to be added.
        :param first_index:     pass list index -n-1..n-1 to insert the first file_obj in each name's register list.
                                values greater than n (==len(file_list)) will append the file_obj to the end of the file
                                object list. the order of the added items will be unchanged if this value is greater
                                or equal to zero. negative values will add the found items in reversed
                                order and **after** the item specified by this index value (so passing -1 will append
                                the items to the end in reversed order, while passing -(n+1) will insert them at the
                                begin in reversed order).
        :return:                list of paths of the added files.
        """
        added_file_paths = list()
        for files in files_register.values():
            added_file_paths.extend(self.add_files(files, first_index=first_index))
        return added_file_paths

    def find_file(self, name: str, properties: Optional[PropertiesType] = None,
                  property_matcher: Optional[Callable[[FileObject, ], bool]] = None,
                  file_sorter: Optional[Callable[[FileObject, ], Any]] = None,
                  ) -> Optional[FileObject]:
        """ find file_obj in this register via properties, property matcher callables and/or file sorter.

        :param name:            file name (stem without extension) to find.
        :param properties:      properties to select the correct file.
        :param property_matcher: callable to match the correct file.
        :param file_sorter:     callable to sort resulting match results.
        :return:                registered/cached file object of the first found/correct file.
        """
        assert not (properties and property_matcher), "pass either properties dict of matcher callable, not both"
        if not property_matcher:
            property_matcher = self.property_watcher
        if not file_sorter:
            file_sorter = self.file_sorter

        file = None
        if name in self:
            files = self[name]
            if len(files) > 1 and (properties or property_matcher):
                if property_matcher:
                    matching_files = [_ for _ in files if property_matcher(_)]
                else:
                    matching_files = [_ for _ in files if _.properties == properties]
                if matching_files:
                    files = matching_files
            if len(files) > 1 and file_sorter:
                files.sort(key=file_sorter)
            file = files[0]
        return file

    def reclassify(self, file_class: Type[FileObject] = CachedFile, **init_kwargs):
        """ re-instantiate all name's file registers items to instances of the class :paramref:`~reclassify.file_class`.

        :param file_class:      the new file object class (see :data:`~ae.files.FileObject`). each found file object
                                will passed to the class constructor (callable) and the return value will then replace
                                the file object in the file list.
        :param init_kwargs:     additional/optional kwargs passed onto the used file_class. pass e.g. the object_loader
                                to use, if :paramref:`~reclassify.file_class` is :class:`CachedFile` (the default file
                                object class).
        """
        for _name, files in self.items():
            for idx, file in enumerate(files):
                files[idx] = file_class(str(file), **init_kwargs)           # type: ignore
