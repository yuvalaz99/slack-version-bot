import asyncio
import aiohttp
from kubernetes import client, config
from datetime import datetime, timezone
import logging
import os

# Get logging level from environment variable, default to INFO if not set
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO))

class KubernetesUtils:
    def __init__(self, application_label_selector_key, app_version_url):
        try:
            self.__load_kubernetes_config()
            self.v1 = client.CoreV1Api()
            self.v1_endpoint_slice = client.DiscoveryV1Api()  # For EndpointSlice API
            self.application_label_selector_key = application_label_selector_key
            self.app_version_url = app_version_url
            self.session = aiohttp.ClientSession() 
        except Exception as e:
            logging.error(f"Error initialize KubernetesUtils: {str(e)}")
    
    def __load_kubernetes_config(self):
        try:
            config.load_incluster_config()
            logging.info("Successfully loaded Kubernetes configuration from within the cluster.")
        except config.ConfigException:
            config.load_kube_config()
            logging.info("Kubernetes configuration loaded from local kubeconfig file.")


    def __construct_label_selector(self, label_selector_value):
        """
        Constructs a label selector using the class property and user-provided value.

        Parameters:
            user_input_value (str): The value to use with the label selector.

        Returns:
            str: The constructed label selector.
        """
        if not label_selector_value:
            return ''
        else:
            label_selector = f"{self.application_label_selector_key}={label_selector_value}"
            logging.info(f"Constructed label selector: {label_selector}")
            return label_selector

    def __get_running_pods(self, namespace, label_selector):
        """
        Retrieves a list of all running pods in the specified namespace and label selector.
        
        Parameters:
            namespace (str): The namespace to search for pods. Defaults to 'default'.
            label_selector (str): Optional filter to get pods by specific labels (e.g., 'app=my-app').
        
        Returns:
            list: A list of dictionaries with pod name, uptime, and IP.
        """
        try:
            field_selector = "status.phase=Running"
            full_label_selector = self.__construct_label_selector(label_selector)
            pod_list = self.v1.list_namespaced_pod(namespace=namespace, label_selector=full_label_selector, field_selector=field_selector)
            running_pods = []

            for pod in pod_list.items:
                creation_time = pod.metadata.creation_timestamp
                uptime_str = self.__calculate_uptime(creation_time)

                running_pods.append({
                    'name': pod.metadata.name,
                    'namespace': pod.metadata.namespace,
                    'ip': pod.status.pod_ip,
                    'uptime': uptime_str
                })

            logging.info(f"Retrieved {len(running_pods)} running pods.")
            return running_pods
        except client.ApiException as e:
            logging.error(f"Error fetching running pods: {str(e)}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error while fetching running pods: {str(e)}")
            return []

    def __calculate_uptime(self, creation_time):
        """Calculates the uptime of a pod based on its creation time."""
        if creation_time:
            uptime = datetime.now(timezone.utc) - creation_time
            return str(uptime).split('.')[0]  # Format uptime as a string
        return "Unknown"

    def __get_endpoint_slices(self, namespace='default'):
        """
        Retrieves EndpointSlices in the specified namespace.
        
        Parameters:
            namespace (str): The namespace to search for EndpointSlices. Defaults to 'default'.
        
        Returns:
            list: A list of EndpointSlice objects.
        """
        try:
            endpoint_slices = self.v1_endpoint_slice.list_namespaced_endpoint_slice(namespace)
            logging.info(f"Retrieved {len(endpoint_slices.items)} EndpointSlices.")
            return endpoint_slices.items
        except client.ApiException as e:
            logging.error(f"Error fetching EndpointSlices: {str(e)}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error while fetching EndpointSlices: {str(e)}")
            return []

    def __filter_endpoints_by_running_pods(self, running_pods, endpoint_slices):
        """
        Filters the endpoints based on the running pods.

        Parameters:
            running_pods (list): List of running pods with their IPs.
            endpoint_slices (list): List of EndpointSlice objects.

        Returns:
            list: Filtered endpoints containing valid pod IPs, ports, and their names.
        """
        try:
            valid_pod_ips = {pod['ip'] for pod in running_pods}  # Set of IPs from running pods
            filtered_endpoints = []
            pod_ip_to_info = {pod['ip']: {'name': pod['name'], 'uptime': pod['uptime'], 'namespace': pod['namespace']} for pod in running_pods}

            for endpoint_slice in endpoint_slices:
                for endpoint in endpoint_slice.endpoints:
                    if endpoint.addresses:  # Ensure there are addresses
                        for address in endpoint.addresses:
                            if address in valid_pod_ips:
                                for port in endpoint_slice.ports:
                                    pod_info = pod_ip_to_info.get(address, {"name": "Unknown Pod", "uptime": "Unknown"})
                                    filtered_endpoints.append({
                                        'name': pod_info['name'],
                                        'namespace': pod_info['namespace'],
                                        'ip': address,
                                        'port': port.port,
                                        'uptime': pod_info['uptime']
                                    })

            return filtered_endpoints
        except Exception as e:
            logging.error(f"Error filtering endpoints by running pods: {str(e)}")
            return []

    async def __get_service_version(self, session, ip, port):
        """
        Fetches the version of a service from the /version endpoint asynchronously.

        Parameters:
            session (aiohttp.ClientSession): The aiohttp session to use for requests.
            ip (str): The IP address of the pod.
            port (int): The port to access the /version endpoint.

        Returns:
            str: The version of the service or empty string if not retrievable.
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://{ip}:{port}{self.app_version_url}"
                async with session.get(url, timeout=3) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        return ""
        except Exception as e:
            logging.error(f"Error fetching version from {ip}:{port}: {str(e)}")
            return ""

    async def __fetch_service_versions(self, filtered_pods):
        """
        Asynchronously fetches service versions for all filtered pods.

        Parameters:
            filtered_pods (list): The filtered pods with their IPs and ports.

        Returns:
            list: A list of service versions.
        """
        async with aiohttp.ClientSession() as session:
            tasks = [self.__get_service_version(session, pod['ip'], pod['port']) for pod in filtered_pods]
            versions = await asyncio.gather(*tasks)
            return versions

    async def __get_pod_logs(self, pod_name, lines, namespace):
        """
        Retrieves the last X lines of logs from a specified pod.
        
        Parameters:
            pod_name (str): The name of the pod to fetch logs from.
            namespace (str): The namespace where the pod is located. Defaults to 'default'.
            lines (int): The number of log lines to retrieve.
        
        Returns:
            str: The logs from the pod or an error message.
        """
        try:
            if not namespace:
                self.v1.read_namespaced_pod_log(name=pod_name, namespace=namespace, tail_lines=lines, async_req=True).get()
            logs = self.v1.read_namespaced_pod_log(name=pod_name, namespace=namespace, tail_lines=lines, async_req=True).get()
            logging.info(f"Retrieved logs for pod {pod_name}.")
            return logs
        except client.ApiException as e:
            logging.error(f"Error fetching logs for pod {pod_name}: {str(e)}")
            return f"Error fetching logs for pod {pod_name}: {str(e)}"
        except Exception as e:
            logging.error(f"Unexpected error while fetching logs for pod {pod_name}: {str(e)}")
            return f"Unexpected error while fetching logs for pod {pod_name}: {str(e)}"

    async def get_service_logs(self, label_selector, namespace, lines):
        """
        Retrieves the last X lines of logs for all running pods in the service.

        Parameters:
            label_selector (str): The label selector to filter the service's pods (e.g., 'app=my-app').
            namespace (str): The namespace where the service and pods are located.
            lines (int): The number of log lines to retrieve for each pod.
        
        Returns:
            str: Formatted logs from all pods in the service.
        """
        try:
            running_pods = self.__get_running_pods(namespace=namespace, label_selector=label_selector)

            if not running_pods:
                return "No running pods found for the specified service."

            logs_results = await asyncio.gather(*[self.__get_pod_logs(pod_name=pod['name'], lines=lines, namespace=pod['namespace']) for pod in running_pods])

            result_str = f"*Service Logs for {label_selector}. Sensitive data will be censored*\n```"
            for pod_name, pod_logs in zip([pod['name'] for pod in running_pods], logs_results):
                result_str += f"\n---- Logs from Pod: {pod_name} ----\n{pod_logs}\n--------------------------------------------\n"

            result_str += "```"  # Close the code block for Slack
            logging.info("Retrieved service logs successfully.")
            return result_str
        
        except Exception as e:
            logging.error(f"Error fetching service logs: {str(e)}")
            return f"Error fetching service logs: {str(e)}"
        
    async def get_services_info(self, label_selector, namespace):        
        """
        Gathers information about running services, their versions, and uptime.

        Parameters:
            label_selector (str): The label selector to filter the service's pods (e.g., 'app=my-app').
            namespace (str): The namespace where the service and pods are located.

        Returns:
            str: Formatted string containing information about the services.
        """
        try:
            running_pods = self.__get_running_pods(namespace=namespace, label_selector=label_selector)
            endpoint_slices = self.__get_endpoint_slices(namespace=namespace)
            filtered_pods = self.__filter_endpoints_by_running_pods(running_pods, endpoint_slices)

            results = []
            if filtered_pods:
                versions = await self.__fetch_service_versions(filtered_pods)
                results = [
                    (pod['name'], pod['ip'], pod['uptime'], versions[i] if versions[i] else "Version Unavailable")
                    for i, pod in enumerate(filtered_pods)
                ]
            else:
                results.append(("No pods were found.", "", "N/A","N/A", "N/A"))
            
            # Create a formatted string for Slack
            result_str = "*Kubernetes Pod Information*\n```"
            result_str += f"{'Pod Name':<35} {'Pod IP':<16} {'Uptime':<20} {'Version':<15}\n" + "-" * 110 + "\n"
        
            for name, ip, uptime, version in results:
                result_str += f"{name:<35} {ip:<16} {uptime:<20} {version:<15}\n"
            
            result_str += "```"  # Close the code block

            return result_str
        
        except Exception as e:
            logging.error(f"Error fetching services information: {str(e)}")
            raise

