import re

def get_version_help_message(label_selector):
    """
    Returns a help message with usage instructions for retrieving service version information.
    
    Args:
        label_selector (str): The label selector used to match Kubernetes services.

    Returns:
        str: The formatted help message for the version command.
    """
    help_message = """
    *Service Version Command Usage:*
    Usage: [--help] namespace="NAMESPACE_NAME" service="SERVICE_NAME"
    
    Parameters:
    - `namespace (optional):` The namespace where the service is located. If not specified, all namespaces will be searched. Example: namespace="default"
    - `service (optional):` The name of the service, matched by Kubernetes label `{label_selector}`. Example: service="my-service"

    Examples:
    - `service=my-service`: Get version information about the service `my-service`.
    - `service=my-service namespace=web`: Get version information about `my-service` in the `web` namespace.
    - `--help`: Display this help message.
    """.format(label_selector=label_selector)
    
    return help_message


def get_logs_help_message(label_selector):
    """
    Returns a help message with usage instructions for retrieving service logs.
    
    Args:
        label_selector (str): The label selector used to match Kubernetes services.

    Returns:
        str: The formatted help message for the logs command.
    """
    help_message = """
    *Service Logs Command Usage:*
    Usage: namespace="NAMESPACE_NAME" service="SERVICE_NAME" lines="NUMBER_OF_LINES"
    
    Parameters:
    - `namespace (optional):` The namespace where the service is located. If not specified, all namespaces will be searched. Example: namespace="default"
    - `service (required):` The name of the service, matched by Kubernetes label `{label_selector}`. Example: service="my-service"
    - `lines (optional):` The number of log lines to retrieve. Example: lines="10"

    Examples:
    - `service=my-service`: Get logs of the service `my-service`.
    - `service=my-service namespace=web`: Get logs of `my-service` in the `web` namespace.
    - `service=my-service lines="20"`: Get the last 20 lines of logs for `my-service`.
    """.format(label_selector=label_selector)
    
    return help_message



def parse_user_input(user_input):
    """
    Parses the user input string to extract the namespace, service, and optional logs flag and lines.
    
    Args:
        user_input (str): The input string from the user.
    
    Returns:
        dict: A dictionary with parsed values for 'namespace', 'service', 'logs', and 'lines'.
    """
    # Removes the @<user_name> from the user input payload
    # payload = user_input.split(' ', 1)[1] if ' ' in user_input else ''
    payload = user_input
    
   # Regular expression to match key-value pairs (key=value)
    key_value_pattern = r'(\w+)=([^\s]+)'  # Match key=value pairs
    # Regular expression to match flags (like --logs or --help)
    flag_pattern = r'(--\w+)'

    # Parse the key-value pairs into a dictionary
    parsed_values = {match[0]: match[1] for match in re.findall(key_value_pattern, payload)}
    
    # Parse optional flags
    flags = re.findall(flag_pattern, payload)
    parsed_values['help'] = "--help" in payload  # Boolean flag for help
    
    return parsed_values
    