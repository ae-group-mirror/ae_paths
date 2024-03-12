"""
generic file path helpers
=========================

this pure python namespace portion is providing useful :ref:`path helper functions` as well as
:ref:`generic system paths` for most platforms, like e.g.:

    * android OS
    * iOS
    * linux
    * macOS
    * Windows

the only external hard dependency of this module are the ae namespace portions :mod:`ae.base` and :mod:`ae.files`.
optional dependencies are:

    * on android OS the PyPi package `jnius`, needed by the functions :func:`user_data_path` and :func:`user_docs_path`.
    * the `plyer` PyPi package, needed by the function :func:`add_common_storage_paths`.


path helper functions
---------------------

the generator functions :func:`coll_files`, :func:`coll_folders` and :func:`coll_items` are building the fundament
for most of the file and folder collection functionality, provided by this module. for example the function
:func:`path_files` is using these generators to determine the files within a folder structure that are matching
the specified wildcards and :ref:`path part placeholders <generic system paths>`. similarly the
function :func:`path_folders` for folders, and :func:`path_items` to collect both, file and folder names.

use the functions :func:`copy_files` and :func:`move_files` to duplicate and move multiple files or entire
file path trees. these two functions are based on :func:`copy_file` and :func:`move_file`.
the functions :func:`copy_tree` and :func:`move_tree` providing an alternative way to copy or move
entire directory trees.

file paths for series of files, e.g. for logging, can be determined via the :func:`series_file_name` function.

the helper function :func:`normalize` converts path strings containing path placeholders into regular path strings,
resolving symbolic links, or is converting paths string from absolute paths to relative paths and vice versa.


generic system paths
--------------------

generic system paths are determined by the following helper functions:

* :func:`app_data_path`: application data path.
* :func:`app_docs_path`: application documents path.
* :func:`user_data_path`: user data path.
* :func:`user_docs_path`: user documents path.

these system paths together with additional generic paths like e.g. the current working directory, storage paths
provided by the `plyer` package, or user and application paths, are provided as `path placeholders`, which get
stored within the :data:`PATH_PLACEHOLDERS` dict by calling the function :func:`add_common_storage_paths`.

:func:`path_name` and :func:`placeholder_path` are converting regular path strings or parts of it into path
placeholders.


file/folder collection and classification
-----------------------------------------

more complex collections of files and folder paths, and the grouping of them, can be done
with the classes :class:`Collector`, described in the underneath section :ref:`collecting files`,
and :class:`FilesRegister`, described in the section :ref:`files register`.

use the :ref:`Collector class <collecting files>` for temporary quick file path searches on your
local file systems as well as on remote servers/hosts. one implementation example is e.g. the method
:meth:`~aedev.pythonanywhere.PythonanywhereApi.deployed_code_files` of the :mod:`aedev.pythonanywhere` module.

the class :ref:`FilesRegister <files register>` helps you to create and cache file path
registers permanently, to quickly find at any time the best fitting match for a requested purpose.
for example the :mod:`~ae.gui_app` module is using it to dynamically select
image/font/audio/... resource files depending on the current user preferences, hardware
and/or software environment.


collecting files
^^^^^^^^^^^^^^^^

to collect file names in the current working directory create an instance of the :class:`Collector` class and call
its :meth:`~Collector.collect` method with a file or folder path, which can contain wildcards::

.. code-block:: python

    from ae.paths import Collector
    coll = Collector()
    coll.collect('*.png')
    image_files_list = coll.files

after that a list containing the found file names can then be retrieved from the :attr:`~Collector.files` attribute.

:meth:`~Collector.collect` can be called multiple times to accumulate and extend the :attr:`~Collector.files` list::

.. code-block:: python

    coll = Collector()
    coll.collect('*.png')
    coll.collect('*.jpg')
    image_files_list = coll.files

multiple calls of :meth:`Collector.collect` can be joined into one code line, because it is returning its instance.
the following statement is equivalent to the last example::

.. code-block:: python

    image_files_list = Collector().collect('*.png').collect('*.jpg').files

by specifying the ``**`` wildcard entire folder trees can be scanned. the following example is collection all
the files, including the hidden ones, in the folder tree under the current working directory::

.. code-block:: python

    test_files = Collector().collect('**/*').collect('**/.*').files

.. hint::
    the second call of the :meth:`Collector.collect` method in this example has to be done only if you are
    using Python's :func:`glob.glob` as the searcher callback, which excludes hidden files (with a leading dot)
    from to match the ``*`` wildcard.

:class:`Collector` is by default only returning files. to also collect folder paths in a deep folder tree, you have
to pass the collecting generator function to the optional :paramref:`~Collector.item_collector` parameter of the
:class:`Collector` class. the accumulated files and folders can then be retrieved from their respective instance
attributes :attr:`~Collector.files`, :attr:`~Collector.paths` and :attr:`~Collector.selected`::

.. code-block:: python

    coll = Collector(item_collector=coll_items)
    coll.collect(...)
    ...
    files = coll.files
    folders = coll.paths
    file_and_folder_items = coll.selected

the found files are provided by the :attr:`Collector.files` instance attribute. found folders will be separately
collected within the :class:`Collector` instance attribute :attr:`~Collector.paths`. the :attr:`~Collector.selected`
attribute contains all found files and folders in a single list.


collect from multiple locations
_______________________________

in a single call of :meth:`~Collector.collect`, providing the method parameters :paramref:`~Collector.collect.append`
or :paramref:`~Collector.collect.select`, you can scan multiple combinations of path prefixes and suffixes, which can
both contain wildcards and folder names, whereas the suffixes containing also parts of the file names to search for.

.. hint:: the wildcards `*`, `**` and `?` are allowed in the prefixes as well as in suffixes.

the resulting file paths are relative or absolute, depending on if the specified prefix(es) containing
absolute or relative paths.

in the following example determines the relative paths of all folders directly underneath the current working directory
with a name that contains the string `'xxx'` or is starting with `'yyy'` or is ending with  `'zzz'`::

.. code-block:: python

    coll = Collector(item_collector=coll_folders)
    coll.collect('', append=('*xxx*', 'yyy*', '*zzz'))
    folders = coll.paths

.. hint:: replace empty string in the first argument of :meth:`~Collector.collect` with '{cwd}' to get absolute paths.

the following example is collecting the absolute paths of files with the name `xxx.cfg` from the first found
location/folder, starting to search in the current working directory, then in the folder above the application
data folder, and finally in a folder with the name of the main application underneath the user data folder::

.. code-block:: python

    coll = Collector()
    coll.collect("{cwd}", "{app}/..", "{usr}/{main_app_name}", append="xxx.cfg")
    found_files = coll.files

to set or change the generic path placeholder parts values, e.g. of the main application name (`{main_app_name}`) and
the application data path (`{app}`), you simply specify their corresponding values as kwargs in the construction
of the :class:`Collector` instance::

.. code-block:: python

    coll = Collector(main_app_name=..., app=...)

additionally you can specify any other path placeholders that will be automatically used and replaced by the
:class:`Collector` instance::

.. code-block:: python

    coll = Collector(any_other_placeholder=...)

by default only the found file(s)/folder(s) of the first combination will be collected. to collect all files instead,
pass an empty tuple to the method argument :paramref:`~Collector.collect.only_first_of` of :meth:`~Collector.collect'::

.. code-block:: python

    coll.collect(..., append=..., [select=..., ] only_first_of=())

add one of the strings `'prefix'`, `'append'` or `'select'` to the :paramref:`~Collector.collect.only_first_of` tuple
argument to collect only the files/folders of the first combination of the specified prefixes, append-suffixes
and select-suffixes.

by using the :paramref:`~Collector.collect.select` argument the found files and folders will additionally be collected
in the :class:`Collector` instance attribute :attr:`~Collector.selected`.

combinations collected via the :paramref:`~Collector.collect.select` argument that are not existing will be logged.
the results are provided by the instance attributes :attr:`~Collector.failed`, :attr:`~Collector.prefix_failed` and
:attr:`~Collector.suffix_failed`.


files register
^^^^^^^^^^^^^^

a files register is an instance of the :class:`FilesRegister`, providing property based file collection and selection,
which is e.g. used by the :mod:`ae.gui_app` ae namespace portion to find and select resource files like icon/image or
sound files.

files can be collected from various places by a single instance of the class :class:`FilesRegister`::

.. code-block:: python

    from ae.paths import FilesRegister

    file_reg = FilesRegister('first/path/to/collect')
    file_reg.add_paths('second/path/to/collect/files/from')

    registered_file = file_reg.find_file('file_name')

in this example the :class:`FilesRegister` instance collects all files that are existing in any sub-folders underneath
the two provided paths. then the :meth:`~FilesRegister.find_file` method will return a file object of type
:class:`~ae.files.RegisteredFile` of the last collected file with the stem (base name w/o extension) `'file_name'`.

multiple files with the same stem can be collected and registered e.g. with different formats, to be selected by
the app by their different properties, which are specified in the folder names underneath the collected paths.
assuming your application is providing an icon image in two sizes, provided
within the following folder structure, situated in the current working directory::

    resources/
        size_72/
            app_icon.jpg
        size_150/
            app_icon.png

when you then create an instance of :class:`FilesRegister` both image files from the `resources` folder will get
registered, interpreting the sub-folder names (`size_*`) as properties or attributes for the registered files,
where `size` will result as the property name and the string after the underscore as the property value.

to retrieve the paths of the application image file with the size ``72``, call the
:meth:`~FilesRegister.find_file` method::

.. code-block:: python

    file_reg = FilesRegister('resources')
    app_icon_image_path = file_reg.find_file('app_icon', dict(size=72))

as a shortcut you can alternatively call the object directly (leaving `.find_file` away)::

.. code-block:: python

    app_icon_image_path = file_reg('app_icon', dict(size=150))

the resulting file path in `app_icon_image_path` will be `"resources/size_72/app_icon.jpg"` in the forelast example
and `"resources/size_150/app_icon.png"` in the last example.

an instance of :class:`FilesRegister` (`file_reg`) behaves like a dict object, where the item key is the file stem
('app_icon') and the item value is a list of instances of :class:`~ae.files.RegisteredFile`. both files in the
resources folder are provided as one dict item::

.. code-block:: python

    file_reg = FilesRegister('resources')
    assert 'app_icon' in file_reg
    assert len(file_reg) == 1
    assert len(file_reg['app_icon']) == 2
    assert isinstance(file_reg['app_icon'][0], RegisteredFile)

for more complex selections you can use callables passed into the :paramref:`~FilesRegister.find_file.property_matcher`
and :paramref:`~FilesRegister.find_file.file_sorter` arguments of :meth:`~FilesRegister.find_file`.
"""
import glob
import os
import shutil
import string
import sys

from collections import defaultdict
from functools import partial
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union, cast

from ae.base import app_name_guess, env_str, norm_path, os_platform                         # type: ignore
from ae.files import CachedFile, FileObject, PropertiesType, RegisteredFile                 # type: ignore


__version__ = '0.3.29'


APPEND_TO_END_OF_FILE_LIST = sys.maxsize
""" special flag default value for the `first_index` argument of the `add_*` methods of :class:`FilesRegister` to
    append new file objects to the end of the name's register file object list.
"""
INSERT_AT_BEGIN_OF_FILE_LIST = -APPEND_TO_END_OF_FILE_LIST
""" special flag default value for the `first_index` argument of the `add_*` methods of :class:`FilesRegister` to
    insert new file objects always at the begin of the name's register file object list.
"""


COLLECTED_FOLDER = None                     #: item type value for a folder|directory|node

CollArgType = Any
""" argument type passed to most callable arguments of :func:`coll_items` except of :paramref:`~coll_items.searcher` """
CollCreatorReturnType = Any
""" type of the return value of the :paramref:`~coll_items.creator` callable, which will be returned to the caller """
CollYieldType = Optional[str]
""" type of collected item, which is either :data:`COLLECTED_FOLDER` for a folder or the file extension for a file """
CollYieldItems = Iterable[tuple[CollYieldType, CollArgType]]
""" type of collected item iterator yielding tuples of (CollYieldType, item[_path]) """

SearcherRetType = Iterable[CollArgType]
""" type of the return value of the callable :paramref:`~coll_items.searcher` argument of :func:`coll_items` """

SearcherType = Callable[[str], SearcherRetType]
""" type of the callable :paramref:`~coll_items.searcher` argument of :func:`coll_items` """


def coll_item_type(item_path: str) -> CollYieldType:
    """ classify path item to be either file, folder or non-existent/excluded/skipped.

    :param item_path:           file/folder path string.
    :return:                    COLLECTED_FOLDER for folders, the file extension for files or None if not found.
    """
    return COLLECTED_FOLDER if os.path.isdir(item_path) else os.path.splitext(item_path)[1]


def coll_items(item_mask: str,
               searcher: SearcherType = cast(SearcherType, partial(glob.glob, recursive=True)),
               selector: Callable[[CollArgType], Union[bool, Any]] = str,
               type_detector: Callable[[CollArgType], CollYieldType] = coll_item_type,
               creator: Callable[[CollArgType], CollCreatorReturnType] = str,  # mypy lacks **creator_kwargs in Callable
               **creator_kwargs
               ) -> CollYieldItems:
    """ determine path-/file-like item(s) specified with optional wildcards by :paramref:`.item_mask`.

    :param item_mask:           file path mask with optional :func:`~glob.glob` wildcards, the '~' shortcut for the
                                home folder path and any :data:`path placeholders <PATH_PLACEHOLDERS>`, which is
                                specifying the files/folders to collect. use the '**' glob as path to include
                                also items from sub-folders deeper than one level.
    :param searcher:            callable to convert|resolve path with optional wildcards in :paramref:`.item_mask`
                                into multiple item file/folder path strings.
    :param type_detector:       callable to typify/classify a found item to be stored in the first tuple items
                                of the returned list. if not passed then :func:`path_item_type` will be used.
    :param selector:            called with each found file/folder name to check if it has to be added to the returned
                                list. the default argument (str) results in returning every file/folder found by glob().
    :param creator:             each found file/folder will be passed as argument to this class/callable and the
                                instance/return-value will be appended as an item to the returned item list.
                                if not passed then the `str` class will be used, which means that the items
                                of the returned list will be strings of the file/folder path and name.
                                passing a class, like e.g. :class:`ae.files.CachedFile`, :class:`ae.files.CachedFile`
                                or :class:`pathlib.Path`, will create instances of this class.
                                alternatively you can pass a callable which will be called on each found file/folder.
                                in this case the return value of the callable will be inserted in the related
                                item of the returned list.
                                silly mypy does not support Union[Type[Any], Callable[[str, KwArg()], Any]].
    :param creator_kwargs:      additional/optional kwargs passed onto the used item_class apart from the item name.
    :return:                    iterator/generator yielding found and selected file system items as instances
                                of the item creator class (passed as :paramref:`.creator` argument, defaulting to
                                the `str` class).
    """
    item_mask = normalize(item_mask, make_absolute=False, remove_dots=False, resolve_sym_links=False)   # substitute '~'

    for coll_arg in searcher(item_mask):
        if selector(coll_arg):
            # noinspection PyArgumentList
            instance = creator(coll_arg, **creator_kwargs)
            yield type_detector(coll_arg), instance


def coll_files(file_mask: str, file_class: Union[Type[Any], Callable] = str, **file_kwargs) -> CollYieldItems:
    """ determine existing file(s) underneath the folder specified by :paramref:`~coll_files.file_mask`.

    :param file_mask:           glob file mask (with optional glob wildcards and :data:`PATH_PLACEHOLDERS`)
                                specifying the files to collect (by default including the sub-folders).
    :param file_class:          factory used for the returned list items (see :paramref:`coll_items.creator`).
                                silly mypy does not support Union[Type[Any], Callable[[str, KwArg()], Any]].
    :param file_kwargs:         additional/optional kwargs apart from file name passed onto the used item_class.
    :return:                    list of files of the class specified by :paramref:`~coll_files.file_mask`.
    """
    yield from coll_items(file_mask, selector=os.path.isfile, creator=file_class, **file_kwargs)


def coll_folders(folder_mask: str, folder_class: Union[Type[Any], Callable] = str, **folder_kwargs) -> CollYieldItems:
    """ determine existing folder(s) underneath the folder specified by :paramref:`~coll_folders.folder_mask`.

    :param folder_mask:         glob folder mask (with optional glob wildcards and :data:`PATH_PLACEHOLDERS`)
                                specifying the folders to collect (by default including the sub-folders).
    :param folder_class:        class or factory used for the returned list items (see :paramref:`~coll_items.creator`).
                                silly mypy does not support Union[Type[Any], Callable[[str, KwArg()], Any]].
    :param folder_kwargs:       additional/optional kwargs apart from file name passed onto the used item_class.
    :return:                    list of folders of the class specified by :paramref:`~coll_folders.folder_mask`.
    """
    yield from coll_items(folder_mask, selector=os.path.isdir, creator=folder_class, **folder_kwargs)


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
    * `sdcard`: SD card root directory (only available in Android if sdcard is inserted).
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
                path = getattr(storagepath, attr)()
                if isinstance(path, str):  # e.g. get_sdcard_dir() returns None in Android device w/o inserted sdcard
                    PATH_PLACEHOLDERS[attr[4:-4]] = path
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


move_tree = shutil.move
""" another alias for :func:`shutil.move` (see also :func:`~ae.paths.move_file`). """


def copy_files(src_folder: str, dst_folder: str, overwrite: bool = False, copier: Callable = copy_file) -> List[str]:
    """ copy files from src_folder into optionally created dst_folder, optionally overwriting destination files.

    :param src_folder:          path to source folder/directory where the files get copied from. placeholders in
                                :data:`PATH_PLACEHOLDERS` will be recognized and substituted.
    :param dst_folder:          path to destination folder/directory where the files get copied to. all placeholders in
                                :data:`PATH_PLACEHOLDERS` are recognized and will be substituted.
    :param overwrite:           pass True to overwrite existing files in the destination folder/directory. on False the
                                files will only get copied if they not exist in the destination.
    :param copier:              copy/move function with src_file and dst_file parameters, returning file path/name.
    :return:                    list of copied files, with their destination path.
    """
    src_folder = normalize(src_folder, make_absolute=False, remove_dots=False, resolve_sym_links=False)
    dst_folder = normalize(dst_folder, make_absolute=False, remove_dots=False, resolve_sym_links=False)

    updated = []

    if os.path.exists(src_folder):
        for src_file in glob.glob(os.path.join(src_folder, '**'), recursive=True):
            if os.path.isfile(src_file):
                dst_file = norm_path(os.path.join(dst_folder, os.path.relpath(src_file, src_folder)))
                if overwrite or not os.path.exists(dst_file):
                    dst_sub_dir = os.path.dirname(dst_file)
                    if not os.path.exists(dst_sub_dir):
                        os.makedirs(dst_sub_dir)
                    updated.append(copier(src_file, dst_file))

    return updated


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
    return copy_files(src_folder, dst_folder, overwrite=overwrite, copier=move_file)


def normalize(path: str, make_absolute: bool = True, remove_base_path: str = "", remove_dots: bool = True,
              resolve_sym_links: bool = True) -> str:
    """ normalize/transform path replacing `PATH_PLACEHOLDERS` and the tilde character (for home folder).

    :param path:                path string to normalize/transform.
    :param make_absolute:       pass False to not convert path to an absolute path.
    :param remove_base_path:    pass a valid base path to return a relative path, even if the argument values of
                                :paramref:`~normalize.make_absolute` or :paramref:`~normalize.resolve_sym_links` are
                                `True`.
    :param remove_dots:         pass False to not replace/remove the `.` and `..` placeholders.
    :param resolve_sym_links:   pass False to not resolve symbolic links, passing True implies a `True` value also for
                                the :paramref:`~normalize.make_absolute` argument.
    :return:                    normalized path string: absolute if :paramref:`~normalize.remove_base_path` is empty and
                                either :paramref:`~normalize.make_absolute` or :paramref:`~normalize.resolve_sym_links`
                                is `True`; relative if :paramref:`~normalize.remove_base_path` is a base path of
                                :paramref:`~normalize.path` or if :paramref:`~normalize.path` got passed as relative
                                path and neither :paramref:`~normalize.make_absolute` nor
                                :paramref:`~normalize.resolve_sym_links` is `True`.
    """
    return norm_path(path.format(**PATH_PLACEHOLDERS),
                     make_absolute=make_absolute,
                     remove_base_path=remove_base_path,
                     remove_dots=remove_dots,
                     resolve_sym_links=resolve_sym_links,
                     )


def path_files(file_mask: str, file_class: Union[Type[Any], Callable] = str, **file_kwargs) -> List[Any]:
    """ determine existing file(s) underneath the folder specified by :paramref:`.file_mask`.

    :param file_mask:           glob file mask (with optional glob wildcards and :data:`PATH_PLACEHOLDERS`)
                                specifying the files to collect (by default including the sub-folders).
    :param file_class:          factory used for the returned list items (see :paramref:`path_items.creator`).
                                silly mypy does not support Union[Type[Any], Callable[[str, KwArg()], Any]].
    :param file_kwargs:         additional/optional kwargs apart from file name passed onto the used item_class.
    :return:                    list of files of the class specified by :paramref:`.file_mask`.
    """
    return path_items(file_mask, selector=os.path.isfile, creator=file_class, **file_kwargs)


def path_folders(folder_mask: str, folder_class: Union[Type[Any], Callable] = str, **folder_kwargs) -> List[Any]:
    """ determine existing folder(s) underneath the folder specified by :paramref:`.folder_mask`.

    :param folder_mask:         glob folder mask (with optional glob wildcards and :data:`PATH_PLACEHOLDERS`)
                                specifying the folders to collect (by default including the sub-folders).
    :param folder_class:        class or factory used for the returned list items (see :paramref:`~path_items.creator`).
                                silly mypy does not support Union[Type[Any], Callable[[str, KwArg()], Any]].
    :param folder_kwargs:       additional/optional kwargs apart from file name passed onto the used item_class.
    :return:                    list of folders of the class specified by :paramref:`.folder_mask`.
    """
    return path_items(folder_mask, selector=os.path.isdir, creator=folder_class, **folder_kwargs)


def path_items(item_mask: str, selector: Callable[[str], Any] = str,
               creator: Union[Type[Any], Callable] = str, **creator_kwargs) -> List[Any]:
    """ determine existing file/folder item(s) underneath the folder specified by :paramref:`.item_mask`.

    :param item_mask:           file path mask (with optional glob wildcards and :data:`PATH_PLACEHOLDERS`)
                                specifying the files/folders to collect.
    :param selector:            called with each found file/folder name to check if it has to be added to the returned
                                list. the default argument (str) results in returning every file/folder found by glob().
    :param creator:             each found file/folder will be passed as argument to this class/callable and the
                                instance/return-value will be appended as an item to the returned item list.
                                if not passed then the `str` class will be used, which means that the items
                                of the returned list will be strings of the file/folder path and name.
                                passing a class, like e.g. :class:`ae.files.CachedFile`, :class:`ae.files.CachedFile`
                                or :class:`pathlib.Path`, will create instances of this class.
                                alternatively you can pass a callable which will be called on each found file/folder.
                                in this case the return value of the callable will be inserted in the related
                                item of the returned list.
                                silly mypy does not support Union[Type[Any], Callable[[str, KwArg()], Any]].
    :param creator_kwargs:      additional/optional kwargs passed onto the used item_class apart from the item name.
    :return:                    list of found and selected items of the item class (:paramref:`.item_mask`).
    """
    return [path for _, path in coll_items(item_mask, selector=selector, creator=creator, **creator_kwargs)]


def path_join(*parts: str) -> str:
    """ join path parts preventing trailing path separator if last part is empty string.

    :param parts:               path parts to join.
    :return:                    joined path string.

    .. hint::
        although :func:`os.path.join` is implemented in C, this function is faster::
        .. code-block:: python

            import os
            import timeit
            from ae.paths import path_join
            paths_secs = timeit.timeit('path_join("test", "sub_test", "sub_sub_test")', globals=globals())
            os_secs = timeit.timeit('os.path.join("test", "sub_test", "sub_sub_test")', globals=globals())
            assert paths_secs < os_secs

        even if you import :func:`os.path.join` without the namespace prefixes, like this::
        .. code-block:: python

            from os.path import join as os_join
            os_secs = timeit.timeit('os_join("test", "sub_test", "sub_sub_test")', globals=globals())
            assert paths_secs < os_secs
    """
    assert parts, "missing required positional argument(s) with path parts to join"

    part_index = len(parts)     # simulate os.path.join() to ignore parts on the left of part with root path
    while part_index:
        part_index -= 1
        if parts[part_index].startswith('/'):
            break
    return '/'.join(_ for _ in parts[part_index:] if _).replace('//', '/')


def path_name(path: str) -> str:
    """ determine placeholder key name of the specified path.

    :param path:                path string to determine name of (can contain placeholders).
    :return:                    name (respectively dict key in :data:`PATH_PLACEHOLDERS`) of the found path
                                or empty string if not found.
    """
    search_path = normalize(path, make_absolute=False, remove_dots=False, resolve_sym_links=False)
    for name, registered_path in PATH_PLACEHOLDERS.items():
        if normalize(registered_path, make_absolute=False, remove_dots=False, resolve_sym_links=False) == search_path:
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
    """ determine non-existent series file name with a unique series index.

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
        from jnius import autoclass         # pylint: disable=no-name-in-module, import-outside-toplevel
        # noinspection PyPep8Naming
        Environment = autoclass('android.os.Environment')  # pylint: disable=invalid-name
        docs_path = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOCUMENTS).getAbsolutePath()

    elif os_platform in ('win32', 'cygwin'):
        docs_path = os.path.join(env_str('USERPROFILE'), 'Documents')

    else:
        docs_path = os.path.expanduser(os.path.join('~', 'Documents'))

    return docs_path


# noinspection PyDictCreation
PATH_PLACEHOLDERS = {}   #: placeholders of user-, os- and app-specific system paths and file name parts

PATH_PLACEHOLDERS['app_name'] = app_name_guess()

PATH_PLACEHOLDERS['ado'] = app_docs_path()
PATH_PLACEHOLDERS['app'] = app_data_path()
PATH_PLACEHOLDERS['cwd'] = os.getcwd()
PATH_PLACEHOLDERS['doc'] = user_docs_path()
PATH_PLACEHOLDERS['usr'] = user_data_path()


class Collector:
    """ file/folder collector class """
    def __init__(self, item_collector: Callable[[str], CollYieldItems] = coll_files, **placeholders):
        """ create new file/folder/item collector instance with individual (extended or overriding) placeholders.

        :param item_collector:  callable to determine the item type to collect. the default is the :func:`coll_files`
                                function. pass e.g. :func:`coll_folders` to collect only folders or :func:`coll_items`
                                to collect both (files and folders). overload the arguments of these functions
                                (with partial) to adapt/change their default arguments.
        :param placeholders:    all other kwargs are placeholders with their names:replacements as keys:values. the
                                placeholders provided by :data:`PATH_PLACEHOLDERS` are available too (but will be
                                overwritten by these arguments).
        """
        self._item_collector = item_collector

        self.paths: List[CollCreatorReturnType] = []            #: list of found/collected folders
        self.files: List[CollCreatorReturnType] = []            #: list of found/collected files
        self.selected: List[CollCreatorReturnType] = []         #: list of found/collected file/folder item instances
        self.failed = 0                                         #: number of not found select-combinations
        self.prefix_failed: Dict[str, int] = defaultdict(int)   #: not found select-combinations count for each prefix
        self.suffix_failed: Dict[str, int] = defaultdict(int)   #: not found select-combinations count for each suffix

        self.placeholders = PATH_PLACEHOLDERS.copy()            #: path part placeholders of this Collector instance
        self.placeholders.update(placeholders)

    def check_add(self, item_mask: str, select: bool = False) -> bool:
        """ check if item mask match file/folder(s) and if yes append accordingly to collecting instance lists.

        :param item_mask:       file/folder mask, optionally including wildcards in the glob.glob format.
        :param select:          pass True to additionally add found files/folders into :attr:`~Collector.selected`.
        :return:                True if at least one file/folder got found/added, else False.
        """
        added_any = False
        for item_type, item_instance in self._item_collector(item_mask):
            if item_type is COLLECTED_FOLDER:
                self.paths.append(item_instance)
            else:
                self.files.append(item_instance)
            if select:
                self.selected.append(item_instance)
            added_any = True

        return added_any

    def _collect_appends(self, prefix: str, appends: Tuple[str, ...], only_first_of: Tuple[str, ...]):
        for suffix in appends:
            mask = path_join(prefix, suffix).format(**self.placeholders)
            if self.check_add(mask) and 'append' in only_first_of:
                return

    def _collect_selects(self, prefix: str, selects: Tuple[str, ...], only_first_of: Tuple[str, ...]):
        for suffix in selects:
            mask = path_join(prefix, suffix).format(**self.placeholders)
            if not self.check_add(mask, select=True):
                self.failed += 1
                self.prefix_failed[prefix] += 1
                self.suffix_failed[suffix] += 1
            elif 'select' in only_first_of:
                return

    def collect(self, *prefixes: str,
                append: Union[str, Tuple[str, ...]] = (), select: Union[str, Tuple[str, ...]] = (),
                only_first_of: Union[str, Tuple[str, ...]] = ('append', 'prefix', 'select', )) -> "Collector":
        """ collect additional files/folders by combining the given prefixes with all the given append/select suffixes.

        .. note:: all arguments of this method can either be passed either as tuples, or for a single value as string.

        :param prefixes:        tuple of file/folder paths to be used as prefix.
        :param append:          tuple of file/folder names to be used as append suffix.
        :param select:          tuple of file/folder names to be used as select suffix. in contrary to
                                :paramref:`.append` is logging not found :paramref:`.prefixes` combinations in the
                                instance attributes :attr:`.failed`, :attr:`prefix_failed` and :attr:`suffix_failed`.
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

        .. hint:: more details and some examples are available in the doc string of this :mod:`module <ae.paths>`.
        """

        if isinstance(append, str):
            append = (append, )
        if isinstance(select, str):
            select = (select, )
        if not append and not select:
            select = ('', )
        if isinstance(only_first_of, str):
            only_first_of = (only_first_of, )

        for prefix in prefixes:
            prefix_count = len(self.paths) + len(self.files)
            if append:
                self._collect_appends(prefix, append, only_first_of)
            if select:
                self._collect_selects(prefix, select, only_first_of)
            if 'prefix' in only_first_of and len(self.paths) + len(self.files) > prefix_count:
                break

        return self

    @property
    def error_message(self) -> str:
        """ returns an error message if an error occurred.

        :return:                error message string if collection failure/error occurred, else an empty string.
        """
        return (f"{self.failed} collection failures"
                + (f" on prefix: {self.prefix_failed}" if self.prefix_failed else "")
                + (f" on suffix: {self.suffix_failed}" if self.suffix_failed else "")
                + f"; found {len(self.paths)} paths, {len(self.files)} files)"
                if self.failed else "")


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
                                object list and values less than n-1 will insert the file_obj to the start of the file.
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
                                the beginning in reversed order).
        :return:                list of paths of the added files.
        """
        increment = -1 if first_index < 0 else 1
        added_file_paths = []
        for file_obj in files:
            self.add_file(file_obj, first_index=first_index)
            added_file_paths.append(str(file_obj))
            first_index += increment
        return added_file_paths

    def add_paths(self, *file_path_masks: str, first_index: int = APPEND_TO_END_OF_FILE_LIST,
                  file_class: Type[FileObject] = RegisteredFile, **init_kwargs) -> List[str]:
        """ add files found in the folder(s) specified by the :paramref:`~add_paths.file_path_masks` args.

        :param file_path_masks: file path masks (with optional wildcards and :data:`~ae.paths.PATH_PLACEHOLDERS`)
                                specifying the files to collect (by default including the sub-folders).
        :param first_index:     pass list index -n-1..n-1 to insert the first file_obj in each name's register list.
                                values greater than n (==len(file_list)) will append the file_obj to the end of the file
                                object list. the order of the added items will be unchanged if this value is greater
                                or equal to zero. negative values will add the found items in reversed
                                order and **after** the item specified by this index value (so passing -1 will append
                                the items to the end in reversed order, while passing -(n+1) will insert them at the
                                beginning in reversed order).
        :param file_class:      the used file object class (see :data:`FileObject`). each found file object will be
                                passed to the class constructor (callable) and added to the list which is an item of
                                this dict.
        :param init_kwargs:     additional/optional kwargs passed onto the used :paramref:`~add_paths.file_class`. pass
                                e.g. the object_loader to use, if :paramref:`~add_paths.file_class` is
                                :class:`CachedFile` (instead of the default: :class:`RegisteredFile`).
        :return:                list of paths of the added files.
        """
        added_file_paths = []
        for mask in file_path_masks:
            added_file_paths.extend(
                self.add_files(path_files(mask, file_class=file_class, **init_kwargs), first_index=first_index))
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
                                beginning in reversed order).
        :return:                list of paths of the added files.
        """
        added_file_paths = []
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
                                will be passed to the class constructor (callable) and the return value will then
                                replace the file object in the file list.
        :param init_kwargs:     additional/optional kwargs passed onto the used file_class. pass e.g. the object_loader
                                to use, if :paramref:`~reclassify.file_class` is :class:`CachedFile` (the default file
                                object class).
        """
        for _name, files in self.items():
            for idx, file in enumerate(files):
                files[idx] = file_class(str(file), **init_kwargs)
