
https://github.com/user-attachments/assets/929df853-1efc-42d1-9e6d-7e8206fdce11
# Slack Version Bot

This project is a Slack chatbot that helps developers easily find the versions of their running applications. The bot lists all running pods in a Kubernetes cluster along with their uptime and version. It also has a command to get the logs for a specific service.

The bot is production-ready, secure, and offers a seamless developer experience. 
## Key Features
- **Security:** The bot scans and censors all sensitive data found in the logs using Microsoft Presidio and TruffleHog, ensuring that sensitive information is not visible in Slack.
- **Helm-based Deployment:** The services are deployed using the same Helm chart for easy management.
- **Modular Design:** The bot's functionality can be easily modified, allowing you to change how the application version is fetched and define the service label selection strategy without rebuilding the code.


## Dependencies and Tools
### Dependencies
- Python >=3.9
- Trufflehug >=3.82.0
### Tools
The bot utilizes the following tools to enhance security by scanning and censoring for sensitive data:

**Microsoft Presidio:** This tool is designed for data protection, providing the ability to identify and redact sensitive information, such as credit card numbers and personally identifiable information (PII), from various sources, including logs. [Learn more about Microsoft Presidio](https://github.com/microsoft/presidio).

**TruffleHog:** TruffleHog scans files for sensitive information, especially credentials and API keys, helping to identify and prevent the accidental exposure of secrets from your logs. [Explore TruffleHog](https://github.com/trufflesecurity/trufflehogs).

## Getting Started

### Installation

1. **Install Trufflehug**
```bash
  curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh | sh -s -- -b /usr/local/bin
```
2. **Install Poetry (dependency manager)**
```bash
  python3 -m pip install --user pipx && python3 -m pipx ensurepath && pipx install poetry==1.8.0 
```
3. **Install Dependencies**
```bash
cd app/
poetry install
```
4. **Set Up Kubernetes Config File:** Ensure you have your Kubernetes config file (usually located at ~/.kube/config) properly configured to connect to your cluster.

5. **Set Environment Variables**

| Variable | Type | Required | Description |
| --- | --- | --- | --- |
| SLACK_BOT_TOKEN | string | true | Slack bot token |
| SLACK_APP_TOKEN | string | true | Slack app token |
| LOG_LEVEL | string | false | Log level |
| APPLICATION_LABEL_SELECTOR_KEY | string | false | Label key that represent the serivce identity |
| APPLICATION_VERSION_URL | string | false | From what url to fetch the service version |

6. **Run the application**
```bash
cd src/
python3 app.py
```

