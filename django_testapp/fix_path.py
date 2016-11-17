import os
import sys

def fix_path():
    current_folder = os.path.abspath(os.path.dirname(__file__))
    lib_path = os.path.join(current_folder, "libs")
    djangae_path = os.path.abspath(os.path.join(current_folder, os.pardir))

    if lib_path not in sys.path:
        sys.path.insert(0, lib_path)

    if djangae_path not in sys.path:
        sys.path.insert(0, djangae_path)

    # Adds Django and Django tests
    base_django_path = os.path.join(current_folder, "submodules", "django")
    django_path = os.path.join(base_django_path, "django")
    django_tests_path = os.path.join(base_django_path, "tests")

    if base_django_path not in sys.path:
        sys.path.insert(0, base_django_path)

    if django_path not in sys.path:
        sys.path.insert(0, django_path)

    if django_tests_path not in sys.path:
        sys.path.insert(0, django_tests_path)

    os.environ['DJANGAE_APP_YAML_LOCATION'] = current_folder
    os.environ['PYTHONPATH'] = ''

    try:
        import wrapper_util
    except ImportError:
        appengine_path = os.path.join(lib_path, "google_appengine")
        sys.path.insert(0, appengine_path)

        simplejson_path = os.path.join(appengine_path, "lib", "simplejson")
        sys.path.insert(0, simplejson_path)
