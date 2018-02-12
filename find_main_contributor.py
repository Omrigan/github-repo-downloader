from __future__ import unicode_literals

import os
import codecs
import json

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LogisticRegression

from download import DATA_DIR


class FindMainContributor(object):

    def __init__(self, vocabulary_size=10000):
        main_contributors, content = [], []
        for root, _, files in os.walk(DATA_DIR):
            for filename in files:
                if '@' in filename:
                    with codecs.open(os.path.join(root, filename)) as f:
                        data = json.loads(f.read())
                        main_contributors.append(self._main_contributor_string(filename, data))
                        content.append(data['readme_content'])

        self._preprocessor = TfidfVectorizer(max_df=0.9, max_features=vocabulary_size)
        self._label_encoder = LabelEncoder()
        self._model = LogisticRegression()
        self._model.fit(
            X=self._preprocessor.fit_transform(content),
            y=self._label_encoder.fit_transform(main_contributors)
        )

    @staticmethod
    def _main_contributor_string(filename, data):
        return 'The main contributor of related GitHub project {} is {}, try to email him at {}'.format(
            filename, data['main_contributor']['name'], data['main_contributor']['email']
        ).encode('utf-8')

    def __call__(self, request):
        return self._label_encoder.inverse_transform(
            self._model.predict(self._preprocessor.transform([request]))
        )[0]


def prompt(find_main_contributor):
    from sys import version_info
    py3 = version_info[0] > 2

    while True:
        request = input('>') if py3 else raw_input('>')
        print(find_main_contributor(request))


if __name__ == "__main__":
    print('Inititalize model...')
    find_main_contributor = FindMainContributor()
    print('Type your query:')
    prompt(find_main_contributor)
