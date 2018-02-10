from __future__ import unicode_literals

import os
import codecs
import json

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import LabelEncoder

from download import DATA_DIR


class FindMainContributor(object):

    def __init__(self, vocabulary_size=100):
        main_contributors, content = [], []
        for root, _, files in os.walk(DATA_DIR):
            for filename in files:
                if '@' in filename:
                    with codecs.open(os.path.join(root, filename)) as f:
                        data = json.loads(f.read())
                        main_contributors.append(self._main_contributor_string(filename, data))
                        content.append(data['readme_content'])

        self._preprocessor = TfidfVectorizer(max_features=vocabulary_size)
        self._label_encoder = LabelEncoder()
        self._model = KNeighborsClassifier(n_neighbors=1)
        self._model.fit(
            X=self._preprocessor.fit_transform(content),
            y=self._label_encoder.fit_transform(main_contributors)
        )

    @staticmethod
    def _main_contributor_string(filename, data):
        return 'main contributor of related GitHub project {} is {}, try to email him at {}'.format(
            filename, data['main_contributor']['name'], data['main_contributor']['email']
        ).encode('utf-8')

    def __call__(self, request):
        return self._label_encoder.inverse_transform(
            self._model.predict(self._preprocessor.transform([request]))
        )[0]


if __name__ == "__main__":
    find_main_contributor = FindMainContributor()
    print find_main_contributor("Who develops web application framework?")
