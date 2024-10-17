import subprocess
import tempfile
import os
import logging

logging.basicConfig(level=logging.ERROR)

class TruffleHogCensor:
    def __init__(self):
        self.censored_content = ""

    def censor_data(self, content: str) -> str:
        """
        Scans for credentials in the provided content using TruffleHog and redacts sensitive information.

        Parameters:
            content (str): The string content to scan for credentials.

        Returns:
            str: The content with sensitive information redacted.
        """
        self.censored_content = content  # Store the original content

        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
            temp_file.write(content.encode('utf-8'))
            temp_file_path = temp_file.name

        # Define the command to run TruffleHog
        command = ["trufflehog", "filesystem", temp_file_path, "json"]

        try:
            # Running the command and capturing the output
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            output = result.stdout

            # Process the output and redact sensitive information
            self._process_trufflehog_output(output)

        except subprocess.CalledProcessError as e:
            logging.error("An error occurred during TruffleHog scan: %s", e.stderr)
            # You might want to raise an exception or handle it accordingly
            raise RuntimeError("TruffleHog scan failed") from e
        
        finally:
            # Remove the temporary file after the scan is done
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

        return self.censored_content

    def _process_trufflehog_output(self, output: str):
        """
        Processes the output from TruffleHog and redacts the detected sensitive data.

        Parameters:
            output (str): The output from the TruffleHog command.

        Returns:
            None: Updates the self.censored_content directly.
        """
        lines = output.splitlines()

        # Process each line of the TruffleHog output
        for line in lines:
            line = line.strip()  # Remove leading/trailing whitespace
            if line.startswith("Raw result:"):
                # Extract the value after "Raw result:"
                raw_result = line.split(":", 1)[1].strip()

                # Redact the sensitive information in the content
                self.censored_content = self.censored_content.replace(raw_result, "******")
