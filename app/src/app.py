import os
import asyncio
import re
import logging
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler
from modules.k8s_utils.k8s_utils import KubernetesUtils
from modules.bot_utils.bot_utils import get_logs_help_message, get_version_help_message, parse_user_input
from modules.sensitive_data_censors.trufflehog_scan import TruffleHogCensor
from modules.sensitive_data_censors.perediso_scan import SensitiveDataCensor

# Set up logging configuration
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO))

APPLICATION_LABEL_SELECTOR_KEY = os.getenv('APPLICATION_LABEL_SELECTOR_KEY', 'app.kubernetes.io/name')
APPLICATION_VERSION_URL = os.getenv('APPLICATION_VERSION_URL', '/version')
                                                     
SLACK_BOT_TOKEN = os.environ['SLACK_BOT_TOKEN']
if not SLACK_BOT_TOKEN:
    raise EnvironmentError("Missing SLACK_BOT_TOKEN in environment variables.")
SLACK_APP_TOKEN = os.environ['SLACK_APP_TOKEN']
if not SLACK_APP_TOKEN:
    raise EnvironmentError("Missing SLACK_APP_TOKEN in environment variables.")

# Set default value of log lines to fetch from a service
DEFAULT_LOG_LINES = 10

# Initialize KubeServiceInfo
kube_utils = KubernetesUtils(application_label_selector_key=APPLICATION_LABEL_SELECTOR_KEY, app_version_url=APPLICATION_VERSION_URL)

# Initialize Slack App
app = AsyncApp(token=SLACK_BOT_TOKEN)

# Initialize sensitive data scanners
sensitive_data_scanner = SensitiveDataCensor()
credentials_data_scanner = TruffleHogCensor()


def censor_data(data):  
    """
    Censors sensitive data from the logs.

    Args:
        data (str): The log data to be censored.
    
    Returns:
        str: The censored log data with sensitive information removed.
    """
    censored_data = credentials_data_scanner.censor_data(data) if data else data
    censored_data = sensitive_data_scanner.censor_sensitive_data(censored_data) if censored_data else data
    return censored_data

async def get_services_info(label_selector, namespace):
    """
    Fetches Kubernetes service information based on label selector and namespace.

    Args:
        label_selector (str): A label selector to filter services (default is empty string for no filtering).
        namespace (str): The namespace to query (default is empty string for all namespaces).
    
    Returns:
        str: Information about the services in the Kubernetes cluster.
    """
    # Call the async method to get Kubernetes service information
    try:
        info = await kube_utils.get_services_info(label_selector=label_selector, namespace=namespace)  
        return info
    except Exception as e:
        logging.error(f"Error retrieving service info: {str(e)}")
        return ("Error retrieving service info")

async def get_service_logs(label_selector, namespace, lines=10):
    """
    Fetches logs of a Kubernetes service and censors sensitive data.

    Args:
        label_selector (str): A label selector to filter the service.
        namespace (str): The namespace of the service.
        lines (int): Number of log lines to fetch (default is 10).
    
    Returns:
        str: The censored logs of the specified service.
    """
    # Call the async method to get Kubernetes service information
    try:
        logs =  await kube_utils.get_service_logs(label_selector=label_selector, namespace=namespace, lines=lines) 
        #Censore all sensitive data from logs
        censored_logs = censor_data(logs)
        
        return censored_logs
    except Exception as e:
        logging.error(f"Error retrieving service logs: {str(e)}")
        return("Error retrieving service logs")
    

@app.command('/version')
async def handle_version_request(ack, body, respond):
    """
    Handles the /version command in Slack. Retrieves the service version information
    based on the user's input, including optional namespace and service details.
    It also supports a --help flag to show usage information.

    Args:
        ack (function): Acknowledge the command request in Slack.
        body (dict): The body of the event received from Slack, containing user input.
        respond (function): The function used to send a response back to the user.

    Returns:
        None: Sends the appropriate response (service info or help) back to the user via Slack.
    """
    try:
        await ack()
        event_payload = body['text']
        logging.info(f"Received event: {event_payload}")
        
        # Parse the input    
        parsed_input = parse_user_input(event_payload)
            
        if parsed_input.get('help', False):
            help_message = get_version_help_message(APPLICATION_LABEL_SELECTOR_KEY)
            await respond(help_message)   
        
        else:      
            namespace = parsed_input.get('namespace', '')  
            service = parsed_input.get('service', None)
            logs = parsed_input.get('logs')
            log_lines = parsed_input.get('lines', DEFAULT_LOG_LINES) 
            
            services_info = await get_services_info(service, namespace)
            logging.info(f"Service Info: {services_info}")
            await respond(services_info)    
    except Exception as e:
        logging.error(f"Error handling /version request: {str(e)}")
        await respond("An error occurred while processing the /version request.")
                
@app.command('/logs')
async def handle_logs_request(ack, body, respond):
    """
    Handles the /logs command in Slack. Retrieves the logs of the specified service,
    with an optional namespace and configurable number of lines to fetch.
    It also supports a --help flag to show usage information.

    Args:
        ack (function): Acknowledge the command request in Slack.
        body (dict): The body of the event received from Slack, containing user input.
        respond (function): The function used to send a response back to the user.

    Returns:
        None: Sends the service logs or help message back to the user via Slack.
    """
    try:
        await ack()
        event_payload = body['text']
        logging.info(f"Received event: {event_payload}")
        
        # Parse the input    
        parsed_input = parse_user_input(event_payload)
            
        if parsed_input.get('help', False):
            help_message = get_logs_help_message(APPLICATION_LABEL_SELECTOR_KEY)
            await respond(help_message)   
        
        else:      
            namespace = parsed_input.get('namespace', '')  
            service = parsed_input.get('service', None)
            log_lines = parsed_input.get('lines', DEFAULT_LOG_LINES) 
            
            # Throw error if user tries to fetch logs but have not entered a service name, which is required
            if not service:
                await respond("Error: 'service' is required when retrieving logs. Use --help to get the bot manual")
            else:
                service_logs = await get_service_logs(service, namespace, log_lines)
                logging.info(f"Service Logs: {service_logs}")
                await respond(service_logs)
    except Exception as e:
        logging.error(f"Error handling /logs request: {str(e)}")
        await respond("An error occurred while processing the /logs request.")
    
async def main():
    handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    await handler.start_async()
    
if __name__ == "__main__":
    asyncio.run(main())
