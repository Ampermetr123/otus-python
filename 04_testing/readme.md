# Программа Scoring c тестами

_Задание по модулю 'Testing' в рамках курса OTUS Python__

Представлены модульные и интеграционный тест, реализованные на базе фреймворка _uinttest_


## Содержимое каталога

- _scoring_ - *http скоринг-сервер* с системой валидацией запросов и реализацией хранилища `store` на базе Redis

- _tests_ - набор тестов для фреймворка `unittest`

## Необходимое программное обеспечение

Для  работы скоринг-сервера:

- интерпретатор Python 3.7 +
- библиотека redis 3.2.0 https://pypi.org/project/redis/
- сервер redis

Для модульного тестирования:

- интерпретатор Python 3.7 +
- библиотека redis 3.2.0 https://pypi.org/project/redis/

Для функционального тестирования
  
- интерпретатор Python 3.7 +
- [библиотека redis 3.2.0](https://pypi.org/project/redis/)
- [библиотека docker 3.7.0](https://pypi.org/project/docker/)
- [библиотека requests](http://docs.python-requests.org/en/master/)
- [docker](https://www.docker.com/)
- [image 'redis' для docker](https://hub.docker.com/_/Redis/) (устанвливается автоматически при наличии доступа к интерент)


## Запуск тестов

Запуск тестов производится из рабочего каталога проекта (в котором располагается настоящий файл).

Запуск модульных тестов:

`python -m unittest discover -s ./tests/unit -v`

Запуск интеграционных теста:

`python -m unittest discover -s ./tests/integration -v`

Запуск функционального теста[^1]:

`python -m unittest discover -s ./tests/functional -v`

[^1]: Перед запуском функционального тестирования необходимо установить переменные окружения. См. файл set_env.bat

Запуск всех тестов:

`python -m unittest discover -s ./tests -v`