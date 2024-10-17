from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.recognizer_registry import recognizer_registry
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from typing import List
import logging

class SensitiveDataCensor:
    def __init__(self, entities: List[str] = None, language: str = 'en'):
        """
        Initialize the SensitiveDataCensor with specified entities and language.

        Parameters:
        - entities (List[str]): A list of entities to be detected. Defaults to a predefined set.
        - language (str): The language for analysis. Defaults to 'en'.
        """
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        # Set default entities if none provided
        if entities is None:
            self.entities = ["CREDIT_CARD", "CRYPTO", "EMAIL_ADDRESS", "IBAN_CODE", "PHONE_NUMBER", "MEDICAL_LICENSE"]
        else:
            self.entities = entities
        
        self.language = language

    def censor_sensitive_data(self, text: str, replacement: str = "******") -> str:
        """
        Detects and censors sensitive data from the input string.

        Parameters:
        - text (str): The input string that may contain sensitive data.
        - replacement (str): The replacement string for sensitive data. Defaults to "******".

        Returns:
        - str: The text with sensitive data censored.
        """
        try:
            # Analyze the text to detect sensitive data
            results = self.analyzer.analyze(text=text, language=self.language, entities=self.entities)

            # Anonymize (censor) the sensitive data by replacing it with the replacement string
            anonymized_text = self.anonymizer.anonymize(
                text=text, 
                analyzer_results=results, 
                operators={"DEFAULT": OperatorConfig("replace", {"new_value": replacement})}
            )
            return anonymized_text.text

        except Exception as e:
            logging.error(f"Error during censorship: {e}")
            raise