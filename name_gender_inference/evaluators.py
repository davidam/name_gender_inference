import json
from urllib.parse import urlencode
from urllib.request import urlopen

import gender_guesser.detector as gender
import requests
from genderize import Genderize, GenderizeException
from hammock import Hammock as NamsorAPI

from name_gender_inference.config import API_KEYS
from name_gender_inference.evaluator import Evaluator
from name_gender_inference.helpers import memoize


class GenderAPIEvaluator(Evaluator):
    """This implementation is for using name pieces"""
    gender_evaluator = 'gender_api'
    api_key = API_KEYS[gender_evaluator]
    gender_response_mapping = {'male': 'm', 'female': 'f'}
    uses_full_name = False
    tuning_params = ['api_' + param for param in ('accuracy', 'samples')]

    def __init__(self, data_source):
        Evaluator.__init__(self, data_source)

    @staticmethod
    @memoize
    def _call_api(n):
        urlpars = urlencode({'key': GenderAPIEvaluator.api_key, 'name': n})
        url = 'https://gender-api.com/get?{}'.format(urlpars)
        response = urlopen(url)
        decoded = response.read().decode('utf-8')
        return json.loads(decoded)

    @classmethod
    def _fetch_gender_with_first_last(cls, first, last):
        api_resp = cls._call_api(first)
        # API call succeeded if no 'errmsg' in json response, else return None and print data
        return api_resp if 'errmsg' not in api_resp else print('\n', api_resp)

    @classmethod
    def _fetch_gender_with_first_mid_last(cls, first, mid, last):
        # If middle name, try various combinations
        connectors = [' ', '-']
        names = [c.join([first, mid]) for c in connectors]
        api_resps = [cls._call_api(n) for n in names]
        api_resp_genders = set([r[cls.api_gender_key_name] for r in api_resps])
        if 'male' not in api_resp_genders and 'female' not in api_resp_genders:
            # If no gender with both names, try first only
            api_resp = cls._call_api(first)
        else:
            # if usage of middle name leads to female or male then take assignment with highest samples
            api_resp = max(api_resps, key=lambda x: x['samples'])
        # API call succeeded if no 'errmsg' in json response, else return None and print data
        return api_resp if 'errmsg' not in api_resp else print('\n', api_resp)

    @classmethod
    def _fetch_gender_with_full_name(cls, full):
        pass

    def preprocess_tuning_params(self):
        for col in self.tuning_params:
            try:
                self.test_data[col] = self.test_data[col].astype(int)
            except:
                self.test_data[col] = self.test_data[col].astype(float)


class GenderAPIFullEvaluator(GenderAPIEvaluator):
    """This implementation is for full_name"""
    gender_evaluator = 'gender_api_full'
    uses_full_name = True

    def __init__(self, data_source):
        GenderAPIEvaluator.__init__(self, data_source)

    @staticmethod
    @memoize
    def _call_api(n):
        urlpars = urlencode({'key': GenderAPIEvaluator.api_key, 'split': n})
        url = 'https://gender-api.com/get?{}'.format(urlpars)
        response = urlopen(url)
        decoded = response.read().decode('utf-8')
        return json.loads(decoded)

    @classmethod
    def _fetch_gender_with_full_name(cls, full):
        api_resp = cls._call_api(full)
        # API call succeeded if no 'errmsg' in json response, else return None and print data
        return api_resp if 'errmsg' not in api_resp else print('\n', api_resp)

    @classmethod
    def _fetch_gender_with_first_last(cls, first, last):
        pass

    @classmethod
    def _fetch_gender_with_first_mid_last(cls, first, mid, last):
        pass


# Used this blog post: https://juliensalinas.com/en/REST_API_fetching_go_golang_vs_python/
# linked from the API's website: https://www.nameapi.org/en/developer/downloads/
class NameAPIEvaluator(Evaluator):
    gender_evaluator = 'name_api'
    api_key = API_KEYS[gender_evaluator]
    url = "http://rc50-api.nameapi.org/rest/v5.0/genderizer/persongenderizer?apiKey="
    gender_response_mapping = {'MALE': 'm', 'FEMALE': 'f'}
    uses_full_name = False
    tuning_params = ['api_confidence']

    def __init__(self, data_source):
        Evaluator.__init__(self, data_source)

    @staticmethod
    @memoize
    def _call_api(name):
        def build_json(n):
            return {
                "inputPerson": {
                    "type": "NaturalInputPerson",
                    "personName": {
                        "nameFields": [
                            {
                                "string": n.title(),
                                "fieldType": "FULLNAME"
                            }
                        ]
                    }
                }
            }

        query = build_json(name)
        url = NameAPIEvaluator.url + NameAPIEvaluator.api_key
        resp = requests.post(url, json=query)
        resp.raise_for_status()
        return resp.json()

    @classmethod
    def _fetch_gender_with_first_last(cls, first, last):
        try:
            api_resp = cls._call_api(first)
            return api_resp
        except requests.exceptions.HTTPError as e:
            print("Bad HTTP status code:", e)
        except requests.exceptions.RequestException as e:
            print("Network error:", e)

    @classmethod
    def _fetch_gender_with_first_mid_last(cls, first, mid, last):
        try:
            # If middle name, try various combinations
            connectors = [' ', '-']
            names = [c.join([first, mid]) for c in connectors]
            api_resps = [cls._call_api(n) for n in names]
            api_resp_genders = set([r[cls.api_gender_key_name] for r in api_resps])
            if 'MALE' not in api_resp_genders and 'FEMALE' not in api_resp_genders:
                # If no gender with both names, try first only
                api_resp = cls._call_api(first)
            else:
                # if usage of middle name leads to female or male then take assignment with highest samples
                api_resp = max(api_resps, key=lambda x: x['confidence'])
            return api_resp
        except requests.exceptions.HTTPError as e:
            print("Bad HTTP status code:", e)
        except requests.exceptions.RequestException as e:
            print("Network error:", e)

    @classmethod
    def _fetch_gender_with_full_name(cls, full):
        pass

    def preprocess_tuning_params(self):
        pass


class NameAPIFullEvaluator(NameAPIEvaluator):
    gender_evaluator = 'name_api_full'
    uses_full_name = True

    def __init__(self, data_source):
        Evaluator.__init__(self, data_source)

    @classmethod
    def _fetch_gender_with_full_name(cls, full):
        try:
            api_resp = cls._call_api(full)
            return api_resp
        except requests.exceptions.HTTPError as e:
            print("Bad HTTP status code:", e)
        except requests.exceptions.RequestException as e:
            print("Network error:", e)

    @classmethod
    def _fetch_gender_with_first_last(cls, first, last):
        pass

    @classmethod
    def _fetch_gender_with_first_mid_last(cls, first, mid, last):
        pass


class NamSorEvaluator(Evaluator):
    gender_evaluator = 'namsor'
    gender_response_mapping = {'male': 'm', 'female': 'f'}
    uses_full_name = False
    tuning_params = ['api_scale']

    def __init__(self, data_source):
        Evaluator.__init__(self, data_source)

    @staticmethod
    @memoize
    def _call_api(name):
        namsor = NamsorAPI('http://api.namsor.com/onomastics/api/json/gender')
        # Namsor takes names that are already properly split on fore- and surname
        if not isinstance(name, tuple):
            raise Exception('When calling NamSor, name must be a tuple')
        else:
            forename, surname = name
        resp = namsor(forename, surname).GET()
        return resp.json()

    @classmethod
    def _fetch_gender_with_first_last(cls, first, last):
        # Call API only with first name only
        api_resp = cls._call_api((first, last))
        # In NamSor response, key 'id' is of no interest. Remove to make comparison later easier
        if 'id' in api_resp:
            api_resp.pop('id')
        # TODO: investigate how hammock deals with errors in API call
        # This will always return something, so if there's an error it won't catch it here
        return api_resp

    @classmethod
    def _fetch_gender_with_first_mid_last(cls, first, mid, last):
        # If middle name, try various combinations
        connectors = [' ', '-']
        names = [c.join([first, mid]) for c in connectors]
        api_resps = [cls._call_api((name, last)) for name in names]
        api_resp_genders = set([r[cls.api_gender_key_name] for r in api_resps])
        if 'male' not in api_resp_genders and 'female' not in api_resp_genders:
            # If no gender with both names is found, use first name only
            api_resp = cls._call_api((first, last))
        else:
            # if usage of middle name leads to female or male then take response with highest confidence
            # confidence in NamSor is absolute value of scale
            api_resp = max(api_resps, key=lambda x: abs(x['scale']))
        if 'id' in api_resp:
            api_resp.pop('id')
        # TODO: investigate how hammock deals with errors in API call
        # This will always return something, so if there's an error it won't catch it here
        return api_resp

    @classmethod
    def _fetch_gender_with_full_name(cls, full):
        pass

    def preprocess_tuning_params(self):
        for col in self.tuning_params:
            self.test_data[col] = self.test_data[col].astype(float).map(lambda x: abs(x))


class GenderGuesserEvaluator(Evaluator):
    """# Python wrapper of Joerg Michael's C-program `gender`"""
    gender_evaluator = 'gender_guesser'
    gender_response_mapping = {'male': 'm', "female": "f", "mostly_male": "m", "mostly_female": "f"}
    uses_full_name = False
    tuning_params = ['api_confidence']

    def __init__(self, data_source):
        Evaluator.__init__(self, data_source)

    @staticmethod
    @memoize
    def _call_api(n):
        return gender.Detector(case_sensitive=False).get_gender(n)

    @classmethod
    def _fetch_gender_with_first_last(cls, first, last):
        api_resp = {'gender': cls._call_api(first)}
        return api_resp

    @classmethod
    def _fetch_gender_with_first_mid_last(cls, first, mid, last):
        # If middle name, connect first with '-', else search with first name only
        name = first + '-' + mid
        g = cls._call_api(name)
        if g != 'unknown':
            api_resp = {'gender': g}
        else:
            name = first
            api_resp = {'gender': cls._call_api(name)}
        return api_resp

    @classmethod
    def _fetch_gender_with_full_name(cls, full):
        pass

    def preprocess_tuning_params(self):
        """Since this service returns no numerical values on confidence or similar we interpret the response values
        nuemrically."""
        response_to_num = {'male': 1.0, 'female': 1.0, 'mostly_male': 0.75, 'mostly_female': 0.75}
        self.test_data['api_confidence'] = 0
        self.test_data.loc[
            self.test_data.api_gender.isin(response_to_num.keys()), 'api_confidence'] = self.test_data[
            self.test_data.api_gender.isin(response_to_num.keys())].api_gender.map(
            lambda x: response_to_num[x])


class GenderizeIoEvaluator(Evaluator):
    gender_evaluator = 'genderize_io'
    # api_key = API_KEYS[gender_evaluator]
    gender_response_mapping = {'male': 'm', "female": "f"}
    uses_full_name = False
    tuning_params = ['api_' + param for param in ['probability', 'count']]

    def __init__(self, data_source):
        Evaluator.__init__(self, data_source)

    @staticmethod
    @memoize
    def _call_api(name):
        return Genderize(api_key=GenderizeIoEvaluator.api_key).get((name,))[0]

    @classmethod
    def _fetch_gender_with_first_last(cls, first, last):
        try:
            api_resp = cls._call_api(first)
            return api_resp
        except GenderizeException as e:
            print('Genderize Exception', e)

    @classmethod
    def _fetch_gender_with_first_mid_last(cls, first, mid, last):
        try:
            # If middle name, try various combinations
            connectors = [' ', '-']
            names = [c.join([first, mid]) for c in connectors]
            api_resps = [cls._call_api(n) for n in names]
            api_resp_genders = set([r[cls.api_gender_key_name] for r in api_resps])
            if 'male' not in api_resp_genders and 'female' not in api_resp_genders:
                # If no gender with both names, try first only
                api_resp = cls._call_api(first)
            else:
                # if usage of middle name leads to female or male then take assignment with highest samples
                # Unknown names have no 'count'
                api_resp = max([ap for ap in api_resps if 'count' in ap], key=lambda x: x['count'])
            return api_resp
        except GenderizeException as e:
            print('Genderize Exception', e)

    @classmethod
    def _fetch_gender_with_full_name(cls, full):
        pass

    def preprocess_tuning_params(self):
        for col in self.tuning_params:
            self.test_data[col] = self.test_data[col].replace({'': 1.0})
            self.test_data[col] = self.test_data[col].astype(float)
