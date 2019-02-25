# Программа Scoring c тестами

_Задание по модулю 'Testing' в рамках курса OTUS Python__

Представлены модульные и интеграционный тест, реализованные на базе фреймворка _uinttest_


## Содержимое каталога

- _scoring_ - *http скоринг-сервер* с системой валидацией запросов и реализацией хранилища `store` на базе Redis

- _tests_ - набор тестов для фреймворка `unittest`

## Необходимое программное обеспечение

Для  работы скоринг-сервера:

- интерпретатор Python 3.6 +
- библиотека redis 3.2.0 https://pypi.org/project/redis/
- сервер redis

Для модульного тестирования:

- интерпретатор Python 3.6 +
- библиотека redis 3.2.0 https://pypi.org/project/redis/

Для интеграционного тестирования
  
- интерпретатор Python 3.6 +
- [библиотека redis 3.2.0](https://pypi.org/project/redis/)
- [библиотека docker 3.7.0](https://pypi.org/project/docker/)
- [библиотека requests](http://docs.python-requests.org/en/master/)
- [docker](https://www.docker.com/)
- [image 'redis' для docker](https://hub.docker.com/_/Redis/) (устанвливается автоматически при наличии доступа к интерент)


## Запуск тестов

Запуск тетстов осущствляется из рабочего каталога проекта (в котором располагается настоящий файл).

Запуск модульных тестов:

`python -m unittest discover -s ./tests/unit -v`

Запуск интеграционного теста:

`python -m unittest discover -s ./tests/integration -v`

Запуск всех тестов:

`python -m unittest discover -s ./tests -v`