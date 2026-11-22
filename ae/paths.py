"""
file paths handling api
=======================

see section :ref:`file paths handling` for more info and examples.
"""
from __future__ import annotations  # allow type forward references (PEP 563), can be removed in Python 3.14+ (PEP 749)

import glob
import importlib
import os
import re
import shutil
import string
import sys

from collections import defaultdict
from collections.abc import Callable, Iterable
from functools import partial
from pathlib import PurePath
from typing import Any

from ae.base import (                                                                       # type: ignore
    UNSET, UnsetType,
    env_str, format_given, norm_path,
    os_path_basename, os_path_dirname, os_path_expanduser, os_path_isdir, os_path_isfile, os_path_join,
    os_path_relpath, os_path_splitext)
from ae.files import CachedFile, FileObject, PropertiesType, RegisteredFile                 # type: ignore
from ae.system import app_name_guess, os_platform                                           # type: ignore


__version__ = '0.4.49'


COLLECTED_FOLDER = UNSET                                            #: item type value for a folder|directory|node


APPEND_TO_END_OF_FILE_LIST = sys.maxsize
""" special flag default value for the `first_index` argument of the `add_*` methods of :class:`FilesRegister` to
    append new file objects to the end of the name's register file object list.
"""
INSERT_AT_BEGIN_OF_FILE_LIST = -APPEND_TO_END_OF_FILE_LIST
""" special flag default value for the `first_index` argument of the `add_*` methods of :class:`FilesRegister` to
    insert new file objects always at the begin of the name's register file object list.
"""

IMAGE_FOLDER = 'img'                                                #: project root images default subfolder name
I18N_FOLDER = 'loc'                                                 #: project root localization/i18n subfolder name
SOUND_FOLDER = 'snd'                                                #: project root audio/sound default subfolder name
RESOURCES_NAMES = (IMAGE_FOLDER, I18N_FOLDER, SOUND_FOLDER)         #: resource types and default subfolder names


type CollArgType = str | os.PathLike[str]
""" argument type passed to most callable arguments of :func:`coll_items` except of :paramref:`~coll_items.searcher` """
type CollCreatorReturnType = Any
""" type of the return value of the :paramref:`~coll_items.creator` callable, which will be returned to the caller """
type CollYieldType = str | UnsetType | None
""" collected item type: :data:`COLLECTED_FOLDER` for a folder, a file extension for a file, or `None` if not found """
type CollYieldItems = Iterable[tuple[CollYieldType, CollArgType]]
""" type of collected item iterator yielding tuples of (CollYieldType, item[_path]) """
type CollCreatorFuncType = Callable[..., CollCreatorReturnType]
""" type of collection item creator callable allowing one :data:`CollArgType` argument and optional multiple kwargs
(:paramref:`coll_items.creator` and :paramref:`path_items.creator`) """

type SearcherRetType = Iterable[CollArgType]
""" type of the return value of the callable :paramref:`~coll_items.searcher` argument of :func:`coll_items` """
type SearcherType = Callable[[str], SearcherRetType]
""" type of the callable :paramref:`~coll_items.searcher` argument of :func:`coll_items` """


def add_common_storage_paths():
    """ add common storage paths to :data:`PATH_PLACEHOLDERS` depending on the operating system (OS). """
    def _add_generic_storage_paths():
        try:
            storagepath = importlib.import_module('plyer').storagepath          # from plyer import storagepath

            for attr in dir(storagepath):
                if attr.startswith('get_') and attr.endswith('_dir'):
                    try:
                        path = getattr(storagepath, attr)()
                        if isinstance(path, str):  # get_sdcard_dir() returns None in Android device w/o inserted sdcard
                            PATH_PLACEHOLDERS[attr[4:-4]] = path
                    except (AttributeError, NotImplementedError, Exception):    # pylint: disable=broad-exception-caught
                        pass
        except (ModuleNotFoundError, ImportError):
            pass

    def _add_win_drive_paths():
        try:
            ctypes = importlib.import_module('ctypes')              # from ctypes import windll, create_unicode_buffer
            create_unicode_buffer, windll = ctypes.create_unicode_buffer, ctypes.windll

            bitmask = windll.kernel32.GetLogicalDrives()
            get_volume_information = windll.kernel32.GetVolumeInformationW
            for letter in string.ascii_uppercase:
                drive_root = letter + ':' + "\\"
                if bitmask & 1 and os_path_isdir(drive_root):
                    buf_len = 64
                    name = create_unicode_buffer(buf_len)
                    get_volume_information(drive_root, name, buf_len, None, None, None, None, 0)
                    PATH_PLACEHOLDERS[name.value] = drive_root.replace("\\", "/")
                bitmask >>= 1
        except (ModuleNotFoundError, ImportError):
            pass

    _add_generic_storage_paths()

    if os_platform == 'linux':
        places = ('/mnt', '/media')
        for place in places:
            if os_path_isdir(place):
                for directory in next(os.walk(place))[1]:
                    PATH_PLACEHOLDERS[directory] = os_path_join(place, directory)

    elif os_platform in ('darwin', 'ios'):
        places = '/Volume'
        if os_path_isdir(places):
            for place in next(os.walk(places))[1]:
                PATH_PLACEHOLDERS[place] = os_path_join(places, place)

    elif os_platform in ('win32', 'cygwin'):
        _add_win_drive_paths()


def app_data_path() -> str:
    """ determine the os-specific absolute path of the {app} directory where user app data can be stored.

    :return:                    path string of the user app data folder.
    """
    return os_path_join(user_data_path(), PATH_PLACEHOLDERS.get('main_app_name', PATH_PLACEHOLDERS['app_name']))


def app_docs_path() -> str:
    """ determine the os-specific absolute path of the {ado} directory where user documents app are stored.

    :return:                    path string of the user documents app folder.
    """
    return os_path_join(user_docs_path(), PATH_PLACEHOLDERS.get('main_app_name', PATH_PLACEHOLDERS['app_name']))


def coll_files(file_mask: str, file_class: type[Any] | Callable = str, **file_kwargs) -> CollYieldItems:
    """ determine existing file(s) underneath the folder specified by :paramref:`.file_mask`.

    :param file_mask:           glob file mask (with optional glob wildcards and :data:`PATH_PLACEHOLDERS`)
                                specifying the files to collect (by default including the subfolders).
    :param file_class:          factory used for the returned list items (see :paramref:`coll_items.creator`).
                                silly mypy does not support (type[Any] | Callable[[str, KwArg()], Any]).
    :param file_kwargs:         additional/optional kwargs apart from the file name passed onto the used item_class.
    :return:                    iterator/generator yielding a 2-item-tuple for each found/matching file.
                                the first tuple-item is the file extension, and the second tuple-item is an instance
                                of the specified :paramref:`.file_class`.
    """
    yield from coll_items(file_mask, selector=os_path_isfile, creator=file_class, **file_kwargs)


def coll_folders(folder_mask: str, folder_class: type[Any] | Callable = str, **folder_kwargs) -> CollYieldItems:
    """ determine existing folder(s) underneath the folder specified by :paramref:`.folder_mask`.

    :param folder_mask:         glob folder mask (with optional glob wildcards and :data:`PATH_PLACEHOLDERS`)
                                specifying the folders to collect (by default including the subfolders).
    :param folder_class:        class or factory used for the returned list items (see :paramref:`coll_items.creator`).
                                silly mypy does not support (type[Any] | Callable[[str, KwArg()], Any]).
    :param folder_kwargs:       additional/optional kwargs apart from the file name passed onto the used item_class.
    :return:                    iterator/generator yielding a 2-item-tuple for each found/matching folder/directory.
                                the first tuple-item is :data:`COLLECTED_FOLDER` (as long as
                                :paramref:`.folder_kwargs` does not overwrite the :paramref:`coll_items.type_detector`
                                argument), and the second tuple-item is an instance of the specified
                                :paramref:`.folder_class`.
    """
    yield from coll_items(folder_mask, selector=os_path_isdir, creator=folder_class, **folder_kwargs)


def coll_item_type(item_path: CollArgType) -> CollYieldType:
    """ classify path item to be either file, folder or non-existent/excluded/skipped.

    :param item_path:           file/folder path string.
    :return:                    COLLECTED_FOLDER for folders, the file extension for files (including the leading dot)
                                or `None` if not found.
    """
    return (COLLECTED_FOLDER if os_path_isdir(item_path) else
            # PyCharm-Type-Checker warnings with: os_path_splitext(item_path)[1] if os_path_isfile(item_path) else
            PurePath(item_path).suffix if os_path_isfile(item_path) else
            None)


def coll_items(item_mask: str,
               searcher: SearcherType = partial(glob.glob, recursive=True),
               selector: Callable[[CollArgType], bool | Any] = str,
               type_detector: Callable[[CollArgType], CollYieldType] = coll_item_type,
               creator: type[Any] | CollCreatorFuncType = str,
               **creator_kwargs
               ) -> CollYieldItems:
    """ determine path-/file-like item(s) specified with optional wildcards by :paramref:`.item_mask`.

    :param item_mask:           file path mask with optional :func:`~glob.glob` wildcards, the "~" shortcut for the
                                home folder path and any :data:`path placeholders <PATH_PLACEHOLDERS>`, which is
                                specifying the files/folders to collect. use the '**' glob wildcard in a path to include
                                also items from subfolders deeper than one level.
    :param searcher:            callable to convert|resolve a path with optional wildcards, specified in
                                :paramref:`.item_mask`, into multiple item file/folder path strings.
    :param type_detector:       callable to typify/classify a found item to be stored in the first tuple items
                                of the returned list, returning :data:`COLLECTED_FOLDER` for a found directory, the
                                file extension of any found file, and `None` if not found. if this argument got not
                                specified, then :func:`coll_item_type` will be used.
    :param selector:            called with each found file/folder name to check if it has to be added to the returned
                                list. the default argument (str) results in returning every file/folder found by glob().
    :param creator:             each found file/folder will be passed as an argument to this class/callable, and the
                                instance/return-value will be appended as an item to the returned item list.
                                if not passed, then the `str` class will be used, which means that the items
                                of the returned list will be strings of the file/folder path and name.
                                passing a class, like e.g. :class:`ae.files.CachedFile`, :class:`ae.files.CachedFile`
                                or :class:`pathlib.Path`, will create instances of this class.
                                alternatively, you can pass a callable which will be called on each found file/folder.
                                in this case the return value of the callable will be inserted in the related
                                item of the returned list.
                                silly mypy does not support ``type[Any] | Callable[[str, KwArg()], Any]``.
    :param creator_kwargs:      additional/optional kwargs passed onto the used item_class apart from the item name.
    :return:                    iterator/generator yielding a 2-item-tuple for each found/matching file system item.
                                the first tuple-item is the file/folder type returned by the specified
                                :paramref:`.type_detector` argument, and the second tuple-item is an instance
                                of the item creator class (specified by the :paramref:`.creator` argument).
    """
    item_mask = normalize(item_mask, make_absolute=False, remove_dots=False, resolve_sym_links=False)   # substitute "~"

    for coll_arg in searcher(item_mask):
        if selector(coll_arg):
            instance = creator(coll_arg, **creator_kwargs)
            yield type_detector(coll_arg), instance


copy_file = shutil.copy2
""" alias for :func:`shutil.copy2` (compatible to :func:`shutil.copy`, :func:`shutil.copyfile` and
:func:`ae.files.copy_bytes`. """


copy_tree = shutil.copytree
""" alias for :func:`shutil.copytree`. """


move_file = shutil.move
""" alias for :func:`shutil.move` (see also :func:`~ae.paths.move_tree`). """


move_tree = shutil.move
""" another alias for :func:`shutil.move` (see also :func:`~ae.paths.move_file`). """


def copy_files(src_folder: str, dst_folder: str, overwrite: bool = False, copier: Callable = copy_file) -> list[str]:
    """ copy files from src_folder into an optionally created dst_folder, optionally overwriting destination files.

    :param src_folder:          path to the source folder / directory where the files get copied from. only the
                                placeholders mapped in :data:`PATH_PLACEHOLDERS` will be recognized and substituted.
    :param dst_folder:          path to the destination folder / directory where the files get copied to. all
                                placeholders in :data:`PATH_PLACEHOLDERS` are recognized and will be substituted.
    :param overwrite:           pass `True` to overwrite existing files in the destination folder/directory.
                                on `False` the files will only get copied if they do not exist in the destination.
    :param copier:              the copy/move function with src_file and dst_file parameters, returning file path/name.
    :return:                    list of copied files, with their destination path.
    """
    src_folder = normalize(src_folder, make_absolute=False, remove_dots=False, resolve_sym_links=False)
    dst_folder = normalize(dst_folder, make_absolute=False, remove_dots=False, resolve_sym_links=False)

    updated = []

    if os_path_isdir(src_folder):
        for src_file in glob.glob(os_path_join(src_folder, '**'), recursive=True):
            if os_path_isfile(src_file):
                dst_path = format_given(os_path_relpath(src_file, src_folder), PATH_PLACEHOLDERS)
                dst_file = norm_path(os_path_join(dst_folder, dst_path))
                if overwrite or not os_path_isfile(dst_file):
                    dst_sub_dir = os_path_dirname(dst_file)
                    if not os_path_isdir(dst_sub_dir):
                        os.makedirs(dst_sub_dir)
                    updated.append(copier(src_file, dst_file))

    return updated


def move_files(src_folder: str, dst_folder: str, overwrite: bool = False) -> list[str]:
    """ move files from src_folder into an optionally created dst_folder, optionally overwriting destination files.

    :param src_folder:          path to the source folder / directory where the files get moved from. placeholders in
                                :data:`PATH_PLACEHOLDERS` will be recognized and substituted.
                                please note that the source folder itself will neither be moved nor removed (but will
                                be empty after the operation is finished).
    :param dst_folder:          path to the destination folder / directory where the files get moved to. all
                                placeholders in :data:`PATH_PLACEHOLDERS` are recognized and will be substituted.
    :param overwrite:           pass `True` to overwrite existing files in the destination folder/directory.
                                on `False` the files will only get moved if they do not exist in the destination.
    :return:                    list of moved files, with their destination path.
    """
    return copy_files(src_folder, dst_folder, overwrite=overwrite, copier=move_file)


def normalize(path: str, make_absolute: bool = True, remove_base_path: str = "", remove_dots: bool = True,
              resolve_sym_links: bool = True) -> str:
    """ normalize/transform a path replacing `PATH_PLACEHOLDERS` and the tilde character (for home folder).

    :param path:                path string to normalize/transform.
    :param make_absolute:       pass `False` to not convert the specified path to an absolute path.
    :param remove_base_path:    pass a valid base path to return a relative path, even if the argument values of
                                :paramref:`.make_absolute` or :paramref:`.resolve_sym_links` are `True`.
    :param remove_dots:         pass `False` to not replace/remove the `.` and `..` placeholders.
    :param resolve_sym_links:   pass `False` to not resolve symbolic links, passing `True` implies a `True` value also
                                for the :paramref:`.make_absolute` argument.
    :return:                    normalized path string: absolute if :paramref:`.remove_base_path` is empty and
                                either :paramref:`.make_absolute` or :paramref:`.resolve_sym_links` is `True`;
                                relative if :paramref:`.remove_base_path` is a base path of :paramref:`.path` or if
                                :paramref:`.path` got passed as a relative path and neither :paramref:`.make_absolute`
                                nor :paramref:`.resolve_sym_links` is `True`.
    """
    return norm_path(format_given(path, PATH_PLACEHOLDERS),
                     make_absolute=make_absolute,
                     remove_base_path=remove_base_path,
                     remove_dots=remove_dots,
                     resolve_sym_links=resolve_sym_links,
                     )


def path_files(file_mask: str, file_class: type[Any] | Callable = str, **file_kwargs) -> list[Any]:
    """ determine existing file(s) underneath the folder specified by :paramref:`.file_mask`.

    :param file_mask:           glob file mask (with optional glob wildcards and :data:`PATH_PLACEHOLDERS`)
                                specifying the files to collect (by default including the subfolders).
    :param file_class:          factory used for the returned list items (see :paramref:`path_items.creator`).
                                silly mypy does not support (type[Any] | Callable[[str, KwArg()], Any]).
    :param file_kwargs:         additional/optional kwargs apart from the file name passed onto the used item_class.
    :return:                    list of files of the class specified by :paramref:`.file_mask`.
    """
    return path_items(file_mask, selector=os_path_isfile, creator=file_class, **file_kwargs)


def path_folders(folder_mask: str, folder_class: type[Any] | Callable = str, **folder_kwargs) -> list[Any]:
    """ determine existing folder(s) underneath the folder specified by :paramref:`.folder_mask`.

    :param folder_mask:         glob folder mask (with optional glob wildcards and :data:`PATH_PLACEHOLDERS`)
                                specifying the folders to collect (by default including the subfolders).
    :param folder_class:        class or factory used for the returned list items (see :paramref:`path_items.creator`).
                                silly mypy does not support (type[Any] | Callable[[str, KwArg()], Any]).
    :param folder_kwargs:       additional/optional kwargs apart from the file name passed onto the used item_class.
    :return:                    list of folders of the class specified by :paramref:`.folder_mask`.
    """
    return path_items(folder_mask, selector=os_path_isdir, creator=folder_class, **folder_kwargs)


def path_items(item_mask: str, selector: Callable[[CollArgType], bool | Any] = str,
               creator: type[Any] | CollCreatorFuncType = str, **creator_kwargs: Any) -> list[Any]:
    """ determine existing file/folder item(s) underneath the folder specified by :paramref:`.item_mask`.

    :param item_mask:           file path mask (with optional glob wildcards and :data:`PATH_PLACEHOLDERS`)
                                specifying the files/folders to collect.
    :param selector:            called with each found file/folder name to check if it has to be added to the returned
                                list. the default argument (str) results in returning every file/folder found by glob().
    :param creator:             each found file/folder will be passed as an argument to this class/callable, and the
                                instance/return-value will be appended as an item to the returned item list.
                                if not passed, then the `str` class will be used, which means that the items
                                of the returned list will be strings of the file/folder path and name.
                                passing a class, like e.g. :class:`ae.files.CachedFile`, :class:`ae.files.CachedFile`
                                or :class:`pathlib.Path`, will create instances of this class.
                                alternatively, you can pass a callable which will be called on each found file/folder.
                                in this case the return value of the callable will be inserted in the related
                                item of the returned list.
                                silly mypy does not support (type[Any] | Callable[[str, KwArg()], Any]).
    :param creator_kwargs:      additional/optional kwargs passed onto the used item_class apart from the item name.
    :return:                    list of found and selected items of the item class (:paramref:`.item_mask`).
    """
    return [path for _, path in coll_items(item_mask, selector=selector, creator=creator, **creator_kwargs)]


def path_join(*parts: str) -> str:
    """ join path parts preventing trailing path separator if last part is empty string.

    :param parts:               path parts to join.
    :return:                    joined path string.
    """
    assert parts, "missing required positional argument(s) with path parts to join"

    part_index = len(parts)     # simulate os.path.join() to ignore parts on the left of a root path part
    while part_index:
        part_index -= 1
        if parts[part_index].startswith("/"):
            break
    return "/".join(_ for _ in parts[part_index:] if _).replace("//", "/")


# noinspection GrazieInspection
_path_match_tokens_to_re = {
    # order of ``**/`` and ``/**`` in the RE tokenization pattern doesn't matter because ``**/`` will be caught first
    # no matter what, making ``/**`` the only option later on.
    # w/o leading or trailing ``/`` two consecutive asterisks will be treated as literals.
    r'/\*\*': r'(?:/.+?)*',     # edge-case #1: catches recursive globs in the middle of a path.
                                # requires an edge case #2 handled after this case.
    r'\*\*/': r'(?:^.+?/)*',    # edge-case #2: catches recursive globs at the start of a path. requires edge case #1
                                # handled before this case. ``^`` is used to ensure a proper location for ``**/``.
    r'\*': r'[^/]*',            # ``[^/]*`` is used to ensure that ``*`` won't match sub-dirs, as with naive ``.*?``.
    r'\?': r'.',
    r'\[\*\]': r'\*',           # escaped special glob character.
    r'\[\?\]': r'\?',           # escaped special glob character.
    r'\[!': r'[^',              # requires to be ordered dict, so that ``\[!`` preceded ``\[`` in the RE mask. needed
    # to differentiate between ``!`` used within character class ``[]`` and outside of it, to avoid faulty conversion.
    r'\[': r'[',
    r'\]': r']',
}
_path_match_replacement = re.compile("(" + '|'.join(_path_match_tokens_to_re).replace('\\', '\\\\\\') + ")")
""" pre-compiled regular expression for :func:`path_match`, inspired by the great SO answer of Pugsley (see
https://stackoverflow.com/questions/27726545/63212852#63212852)
"""


def path_match(path: str, mask: str) -> bool:
    """ return `True` if the specified path matches the specified path mask/pattern.

    :param path:                path string to match.
    :param mask:                path mask/pattern including glob-like wildcards.
    :return:                    `True` if the path specified by :paramref:`.path` matches the mask/pattern specified by
                                the :paramref:`.mask` argument.
    """
    if sys.version_info < (3, 13):
        re_mask = _path_match_replacement.sub(lambda _match: _path_match_tokens_to_re[_match.group()], re.escape(mask))
        match = bool(re.fullmatch(re_mask, path))
    else:
        # noinspection PyUnusedLocal
        match = PurePath(path).full_match(mask)                 # pylint: disable=no-member
    return match


def path_name(path: str) -> str:
    """ determine the placeholder key name of the specified path.

    :param path:                path string to determine its placeholder key name of (can contain placeholders).
    :return:                    name (respectively dict key in :data:`PATH_PLACEHOLDERS`) of the found path
                                or empty string if not found.
    """
    search_path = normalize(path, make_absolute=False, remove_dots=False, resolve_sym_links=False)
    for name, registered_path in PATH_PLACEHOLDERS.items():
        if normalize(registered_path, make_absolute=False, remove_dots=False, resolve_sym_links=False) == search_path:
            return name
    return ""


def paths_match(paths: Iterable[str], masks: Iterable[str]) -> Iterable[str]:
    """ filter the paths matching at least one of the specified glob-like wildcard masks.

    :param paths:               iterable of path strings to be checked if they match at least one pattern/mask,
                                specified by the :paramref:`.masks` argument.
    :param masks:               iterable of path masks/pattern with glob-like wildcards.
    :return:                    iterator, yielding the paths specified by :paramref:`.paths` that are
                                matching at least one mask, specified by the :paramref:`.masks` argument.
    """
    for path in paths:
        for mask in masks:
            if path_match(path, mask):
                yield path
                break


def placeholder_key(path: str) -> str:
    """ determine :data:`PATH_PLACEHOLDERS` key of the specified path.

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
    """ replace the beginning of the specified path string with the longest prefix found in :data:`PATH_PLACEHOLDERS`.

    :param path:                path string (optionally including subfolders and file name).
    :return:                    path string with replaced placeholder prefix (if found).
    """
    for key in sorted(PATH_PLACEHOLDERS, key=lambda k: len(PATH_PLACEHOLDERS[k]), reverse=True):
        val = PATH_PLACEHOLDERS[key]
        if path == val or path.replace("\\", "/").startswith(val + "/"):
            return '{' + key + '}' + path[len(val):]
    return path


def relative_file_paths(root_path: str, path_masks: list[str], skip_file_path: Callable[[str], bool] = lambda _: False
                        ) -> set[str]:
    """ find all files underneath the specified root path, e.g. to collect the .py modules of a python package.

    :param root_path:           path of the root folder. pass empty string to use the current working directory.
    :param path_masks:          list of folder or subpackage path masks with glob-wildcards, relative to the root path.
    :param skip_file_path:      called for each found file with their file path (relative to the project root folder in
                                :paramref:`.root_path`) as argument, returning `True` to exclude/skip the specified
                                file.
    :return:                    set of file paths relative to the root folder specified by the argument
                                :paramref:`.root_path`.
    """
    file_paths = set()
    for path_mask in path_masks:
        for file_path in glob.glob(os_path_join(root_path, path_mask), recursive=True):
            if os_path_isfile(file_path) and not skip_file_path(file_path):
                file_paths.add(os_path_relpath(file_path, root_path))

    return file_paths


def resources_folder_names(resource_types: Iterable[str] = RESOURCES_NAMES,
                           path_placeholders: dict[str, str] | None = None) -> list[str]:
    """ folder names of image, locale and audio/sound resources.

    :param resource_types:      resource types to determine their standard and app/user-specific folder names for.
    :param path_placeholders:   path placeholders dict (used by pjm to pass project-specific placeholders).
    :return:                    list of the app/user-specific folder names (defined in :paramref:`.path_placeholders`),
                                followed by all the default resource subfolder names, of the (in
                                :paramref:`.resource_types`) specified resource types.
    """
    if path_placeholders is None:
        path_placeholders = PATH_PLACEHOLDERS

    folder_names = []
    for folder_name in resource_types:
        configured_folder_name = path_placeholders.get(folder_name)
        if configured_folder_name and configured_folder_name != folder_name:
            folder_names.append(configured_folder_name)

    return folder_names + [*resource_types]    # add standard folder name


def series_file_name(file_path: str, digits: int = 2, marker: str = " ", create: bool = False) -> str:
    """ determine non-existent series file name with a unique series index.

    :param file_path:           file path and name (optional with extension).
    :param digits:              number of digits used for the series index.
    :param marker:              marker that will be put at the end of the file name and before the series index.
    :param create:              pass `True` to create the file (to reserve the series index).
    :return:                    the file path extended with a unique / new series index.
    """
    path_stem, ext = os_path_splitext(file_path)
    path_stem += marker

    found_files = glob.glob(path_stem + "*" + ext)
    index = len(found_files) + 1
    while True:
        file_path = path_stem + format(index, "0" + str(digits)) + ext
        if not os_path_isfile(file_path):
            break
        index += 1

    if create:
        open(file_path, 'w').close()        # pylint: disable=consider-using-with, unspecified-encoding

    return file_path


def skip_py_cache_files(file_path: str) -> bool:
    """ file exclusion callback for the files under Python's cache folders.

    :param file_path:       path to file to check for exclusion, relative to the project root folder.
    :return:                `True` if the file specified in :paramref:`.file_path` has to be excluded, else `False`.
    """
    return '__pycache__' in file_path.split("/")


def user_data_path() -> str:
    """ determine the os-specific absolute path of the {usr} directory where the app user data can be stored.

    :return:    path string of the user data folder.
    """
    if os_platform == 'android':
        jnius = importlib.import_module('jnius')
        android_class = getattr(jnius, 'autoclass')
        android_cast = getattr(jnius, 'cast')
        python_activity = android_class('org.kivy.android.PythonActivity')
        context = android_cast('android.content.Context', python_activity.mActivity)
        files_path = android_cast('java.io.File', context.getFilesDir())
        data_path = files_path.getAbsolutePath()

    elif os_platform in ('win32', 'cygwin'):
        data_path = env_str('APPDATA') or os_path_expanduser("~")

    else:
        if os_platform == 'ios':
            data_path = "Documents"
        elif os_platform == 'darwin':
            data_path = os_path_join("Library", "Application Support")
        else:                                       # platform == 'linux' or 'freebsd' or anything else
            data_path = env_str('XDG_CONFIG_HOME') or ".config"

        if not os.path.isabs(data_path):
            data_path = os_path_expanduser(os_path_join("~", data_path))

    return data_path


def user_docs_path() -> str:
    """ determine the os-specific absolute path of the {doc} directory where the user is storing the personal documents.

    :return:                    path string of the user documents folder.
    """
    if os_platform == 'android':
        android_env = importlib.import_module('jnius').autoclass('android.os.Environment')
        return android_env.getExternalStoragePublicDirectory(android_env.DIRECTORY_DOCUMENTS).getAbsolutePath()

    if os_platform in ('win32', 'cygwin'):
        return os_path_join(env_str('USERPROFILE') or os_path_expanduser("~"), "Documents")

    return os_path_expanduser(os_path_join("~", "Documents"))


PATH_PLACEHOLDERS = {
    'app_name': app_name_guess()}
""" placeholders dict of path parts and user-, os- and app-specific system paths """
PATH_PLACEHOLDERS.update({      # postponed update, because app_docs_path() requires PATH_PLACEHOLDERS['app_name']
    'ado': app_docs_path(),     # app documents path
    'app': app_data_path(),     # app data path
    'cwd': os.getcwd(),         # current working directory
    'doc': user_docs_path(),    # user documents path
    'usr': user_data_path(),    # user data path
})
PATH_PLACEHOLDERS.update(       # subfolder default names (for docs, resources, templates and unit tests)
    {_name: _name for _name in RESOURCES_NAMES})


class Collector:                                                    # pylint: disable=too-many-instance-attributes
    """ file/folder collector class """
    def __init__(self, item_collector: Callable[[str], CollYieldItems] = coll_files, **placeholders):
        """ create a new file / folder / item collector instance with individual (extended or overriding) placeholders.

        :param item_collector:  callable to determine the item type to collect. the default is the :func:`coll_files`
                                function. pass e.g. :func:`coll_folders` to collect only folders or :func:`coll_items`
                                to collect both (files and folders). overload the arguments of these functions
                                (with partial) to adapt/change their default arguments.
        :param placeholders:    all other kwargs are placeholders with their names:replacements as keys:values. the
                                placeholders provided by :data:`PATH_PLACEHOLDERS` are available too (but will be
                                overwritten by these arguments).
        """
        self._item_collector = item_collector

        self.paths: list[CollCreatorReturnType] = []            #: list of found/collected folders
        self.files: list[CollCreatorReturnType] = []            #: list of found/collected files
        self.selected: list[CollCreatorReturnType] = []         #: list of found/collected files/folders item instances
        self.failed = 0                                         #: number of not found select-combinations
        self.prefix_failed: dict[str, int] = defaultdict(int)   #: not found select-combinations count for each prefix
        self.suffix_failed: dict[str, int] = defaultdict(int)   #: not found select-combinations count for each suffix

        self.placeholders = PATH_PLACEHOLDERS.copy()            #: path part placeholders of this Collector instance
        self.placeholders.update(placeholders)

    def check_add(self, item_mask: str, select: bool = False) -> bool:
        """ check if the item mask matches file/folder(s) and if yes, appends accordingly to collecting instance lists.

        :param item_mask:       file/folder mask, optionally including wildcards in the glob.glob format.
        :param select:          pass `True` to additionally add found files/folders into :attr:`~Collector.selected`.
        :return:                `True` if at least one file/folder got found/added, else `False`.
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

    def _collect_appends(self, prefix: str, appends: tuple[str, ...]):
        for suffix in appends:
            mask = format_given(path_join(prefix, suffix), self.placeholders)
            self.check_add(mask)

    def _collect_selects(self, prefix: str, selects: tuple[str, ...]):
        for suffix in selects:
            mask = format_given(path_join(prefix, suffix), self.placeholders)
            if not self.check_add(mask, select=True):
                self.failed += 1
                self.prefix_failed[prefix] += 1
                self.suffix_failed[suffix] += 1

    def collect(self, *prefixes: str,
                append: str | tuple[str, ...] = (),
                select: str | tuple[str, ...] = ()) -> Collector:
        """ collect additional files/folders by combining the given prefixes with all the given append/select suffixes.

        :param prefixes:        at least one or multiple file/folder paths, with wildcards, to be used as prefixes.
        :param append:          tuple of file/folder names to be used as suffixes or a single suffix as string argument.
        :param select:          tuple of file/folder names to be used as suffixes or a single suffix as string argument.
                                in contrary to :paramref:`.append`, matches of this argument are getting counted if
                                they not get found in combination with any of the :paramref:`.prefixes`. the counters
                                are provided in the instance attributes :attr:`.failed`, :attr:`.prefix_failed` and
                                :attr:`.suffix_failed`.
        :raises:                `AssertionError` if no prefixes are specified.
        """
        assert prefixes, "ae.paths.Collector.collect(): at least one prefix has to be specified"
        if isinstance(append, str):
            append = (append, )
        if isinstance(select, str):
            select = (select, )
        if not append and not select:
            select = ('', )

        for prefix in prefixes:
            if append:
                self._collect_appends(prefix, append)
            if select:
                self._collect_selects(prefix, select)

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
    """ files register catalog - see also :ref:`files register` examples. """
    def __init__(self, *add_path_args,
                 property_matcher: Callable[[FileObject, ], bool] | None = None,
                 file_sorter: Callable[[FileObject, ], Any] | None = None,
                 **add_path_kwargs):
        """ create a files register instance.

        :param add_path_args:   if at least one argument get specified, then :meth:`~FilesRegister.add_paths` will be
                                called with all the specified non-keyword-arguments and with the specified kwargs
                                (apart from :paramref:`~FilesRegister.property_matcher`
                                and :paramref:`~FilesRegister.file_sorter`).
        :param property_matcher: file properties matcher callable, used as the default by
                                :meth:`~FilesRegister.find_file` if not specified there.
        :param file_sorter:     file sorter callable, used as the default value by
                                :meth:`~FilesRegister.find_file` if not specified there.
        :param add_path_kwargs: passed onto call of :meth:`~FilesRegister.add_paths` if the
                                :paramref:`~FilesRegister.add_path_args` got provided by the caller.
        """
        super().__init__()
        self.property_watcher = property_matcher
        self.file_sorter = file_sorter
        if add_path_args:
            self.add_paths(*add_path_args, **add_path_kwargs)

    def __call__(self, *find_args, **find_kwargs) -> FileObject | None:
        """ add_path_args and kwargs will be completely redirected to :meth:`~FilesRegister.find_file`. """
        return self.find_file(*find_args, **find_kwargs)

    def add_file(self, file_obj: FileObject, first_index: int = APPEND_TO_END_OF_FILE_LIST):
        """ add a single file to the list of this dict mapped by the file-name/stem as a dict key.

        :param file_obj:        either file path string or any object with a `stem` attribute.
        :param first_index:     pass list index -n-1..n-1 to insert :paramref:`.file_obj` in the name's list.
                                values greater than n (==len(file_list)) will append the file_obj to the end of the file
                                object list, and values less than n-1 will insert the file_obj to the start of the file.
        """
        name = os_path_splitext(os_path_basename(file_obj))[0] if isinstance(file_obj, str) else file_obj.stem
        if name in self:
            list_len = len(self[name])
            if first_index < 0:
                first_index = max(0, list_len + first_index + 1)
            else:
                first_index = min(first_index, list_len)
            self[name].insert(first_index, file_obj)
        else:
            self[name] = [file_obj]

    def add_files(self, files: Iterable[FileObject], first_index: int = APPEND_TO_END_OF_FILE_LIST) -> list[str]:
        """ add files from another :class:`FilesRegister` instance.

        :param files:           iterable with file objects to be added.
        :param first_index:     pass list index -n-1..n-1 to insert the first file_obj in each name's register list.
                                values greater than n (==len(file_list)) will append the file_obj to the end of the file
                                object list. the order of the added items will be unchanged if this value is greater or
                                equal to zero. negative values will add the items from :paramref:`.files` in
                                reversed order, and **after** the item specified by this index value. so passing -1 will
                                append the items to the end in reversed order and passing -(n+1) will insert them at
                                the beginning in reversed order.
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
                  file_class: type[FileObject] = RegisteredFile, **init_kwargs) -> list[str]:
        """ add files found in the folder(s) specified by the :paramref:`.file_path_masks` args.

        :param file_path_masks: file path masks (with optional wildcards and :data:`~ae.paths.PATH_PLACEHOLDERS`)
                                specifying the files to collect (by default including the subfolders).
        :param first_index:     pass list index -n-1..n-1 to insert the first file_obj in each name's register list.
                                values greater than n (==len(file_list)) will append the file_obj to the end of the file
                                object list. the order of the added items will be unchanged if this value is greater
                                or equal to zero. negative values will add the found items in reversed
                                order, and **after** the item specified by this index value. so passing -1 will append
                                the items to the end in reversed order, while passing -(n+1) will insert them at the
                                beginning in reversed order.
        :param file_class:      the used file object class (see :data:`FileObject`). each found file object will be
                                passed to the class constructor (callable) and added to the list, which is an item of
                                this dict.
        :param init_kwargs:     additional/optional kwargs passed onto the used :paramref:`.file_class`. pass
                                e.g., the object_loader to use, if :paramref:`.file_class` is
                                :class:`CachedFile` (instead of the default: :class:`RegisteredFile`).
        :return:                list of paths of the added files.
        """
        added_file_paths = []
        for mask in file_path_masks:
            added_file_paths.extend(
                self.add_files(path_files(mask, file_class=file_class, **init_kwargs), first_index=first_index))
        return added_file_paths

    def add_register(self, files_register: FilesRegister, first_index: int = APPEND_TO_END_OF_FILE_LIST) -> list[str]:
        """ add files from another :class:`FilesRegister` instance.

        :param files_register:  the :class:`FilesRegister` instance containing the file_obj to be added.
        :param first_index:     pass list index -n-1..n-1 to insert the first file_obj in each name's register list.
                                values greater than n (==len(file_list)) will append the file_obj to the end of the file
                                object list. the order of the added items will be unchanged if this value is greater
                                or equal to zero. negative values will add the found items in reversed
                                order, and **after** the item specified by this index value. so passing -1 will append
                                the items to the end in reversed order, while passing -(n+1) will insert them at the
                                beginning in reversed order.
        :return:                list of paths of the added files.
        """
        added_file_paths = []
        for files in files_register.values():
            added_file_paths.extend(self.add_files(files, first_index=first_index))
        return added_file_paths

    def find_file(self, name: str, properties: PropertiesType | None = None,
                  property_matcher: Callable[[FileObject, ], bool] | None = None,
                  file_sorter: Callable[[FileObject, ], Any] | None = None,
                  ) -> FileObject | None:
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

    def reclassify(self, file_class: type[FileObject] = CachedFile, **init_kwargs):
        """ reinstantiate all name's files registers items to instances of the class :paramref:`.file_class`.

        :param file_class:      the new file object class (see :data:`~ae.files.FileObject`). each found file object
                                will be passed to the class constructor (callable) and the return value will then
                                replace the file object in the file list.
        :param init_kwargs:     additional/optional kwargs passed onto the used file_class. pass e.g., the object_loader
                                to use, if :paramref:`.file_class` is :class:`CachedFile` (the default file
                                object class).
        """
        for _name, files in self.items():
            for idx, file in enumerate(files):
                files[idx] = file_class(str(file), **init_kwargs)
