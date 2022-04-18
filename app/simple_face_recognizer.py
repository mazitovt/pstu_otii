import enum
import os
import sqlite3
from typing import Dict, List, Tuple
import face_recognition
import numpy as np
from cv2 import cv2 as mycv2
from datetime import datetime as dt


class UploadedPhotosStatus(enum.Enum):
    processed = 0
    to_process = 1


def _create_encoding(contents):
    """
    Создает кодировку лица  на изображения
    :param contents:
    :return:
    """
    rgb_img = get_rgb_img(contents)
    img_enc = face_recognition.face_encodings(rgb_img)[0]

    return img_enc


def get_rgb_img(contents):
    """
    Кодирует изображение из массива байтов
    :param contents:
    :return:
    """
    buffer = np.fromstring(contents, np.uint8)
    img_np = mycv2.imdecode(buffer, mycv2.IMREAD_COLOR)
    rgb_img = mycv2.cvtColor(img_np, mycv2.COLOR_BGR2RGB)
    return rgb_img


def check_folder(folder_path) -> None:
    """
    Создает каталог, если он не существует
    :param folder_path: абсолютный путь к каталогу
    :return:
    """
    if not os.path.isdir(folder_path):
        os.mkdir(folder_path)


def count_people(rgb_img):
    return len(face_recognition.face_locations(rgb_img))


class SimpleFaceRecognizer:

    def __init__(self, config: Dict):
        self._connectiondb = sqlite3.connect(config["sqlite"])
        self._encodings_dir = os.path.join(os.path.dirname(__file__), config["encodings_dir"])
        self._str_person_encoding = "person_encoding"

        self._frame_resizing = 0.25
        self._known_face_encodings = []
        self._known_face_names = []

        check_folder(self._encodings_dir)

        self._load_images()
        self._uploaded_photos_status = UploadedPhotosStatus.processed

    def _execute_query(self, query: str) -> None:
        """
        Выполняет запрос к бд
        :param query: запрос
        :return:
        """
        cursor = self._connectiondb.cursor()
        cursor.execute(query)
        self._connectiondb.commit()
        cursor.close()

    def _get_query_result(self, query: str) -> List[Tuple]:
        """
        Выполняет запрос к бд и возвращает его результат
        :param query: запрос
        :return: результат запроса
        """
        cursor = self._connectiondb.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        self._connectiondb.commit()
        cursor.close()

        return result

    def _save_encoding(self, encoding) -> str:
        """
        Сохраняет массив в файл и возвращет путь к файлу
        :param encoding: массив
        :return: путь к файлу
        """
        while os.path.exists(
                file_path := os.path.join(self._encodings_dir, dt.now().strftime("%Y-%m-%dT%H_%M_%S") + ".npy")
        ):
            pass

        with open(file_path, "wb") as f:
            np.save(f, encoding)

        return file_path

    def _read_encoding(self, file_path) -> np.ndarray:
        """
        Читает массив из файла по пути
        :param file_path: абсолютный путь к файлу
        :return: прочитанный массив
        """
        with open(os.path.join(self._encodings_dir, file_path), 'rb') as f:
            return np.load(f)

    def _load_images(self):
        """
        Загружает людей из базы
        :param:
        :return:
        """
        self._known_face_names = []
        self._known_face_encodings = []

        for row in self._get_query_result(f"SELECT * FROM {self._str_person_encoding}"):
            name = row[0]
            file_path = row[1]

            self._known_face_encodings.append(self._read_encoding(file_path))
            self._known_face_names.append(name)

    def add_person(self, name, contents) -> bool:
        """
        Добавляет нового человека в базу. Если на изображении не один человек, то возвращет False
        :param name:
        :param contents:
        :return: успешность добавления нового человека в бд
        """
        img_enc = _create_encoding(contents)

        if count_people(get_rgb_img(contents)) == 1:
            file_path = self._save_encoding(img_enc)
            self._execute_query(f"INSERT INTO person_encoding VALUES ('{name}', '{os.path.basename(file_path)}')")
            self._uploaded_photos_status = UploadedPhotosStatus.to_process
            return True
        else:
            return False

    def load_new_images(self) -> None:
        """
        Загружает людей из базы, если только были произведены изменения (пока только добавление)
        :return:
        """
        if self._uploaded_photos_status == UploadedPhotosStatus.to_process:
            self._load_images()
        self._uploaded_photos_status = UploadedPhotosStatus.processed

    def detect_known_faces(self, contents) -> List[str]:
        """
        Распознает известные лица на фотографии и возвращает их имена
        :param contents: изображение в форме bytes
        :return: список
        """
        rgb_img = get_rgb_img(contents)
        # rgb_img = mycv2.resize(rgb_img, (0, 0), fx=self._frame_resizing, fy=self._frame_resizing)
        face_locations = face_recognition.face_locations(rgb_img)
        face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

        face_names = []
        for face_encoding in face_encodings:
            # Сравниваем лицо на изображении со всеми известными лицами
            matches = face_recognition.compare_faces(self._known_face_encodings, face_encoding, tolerance=0.6)
            name = "Unknown"

            # Получаем расстояния от лица на изображении до известных лиц
            face_distances = face_recognition.face_distance(self._known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = self._known_face_names[best_match_index]
            face_names.append(name)

        return face_names

    def known_faces(self):
        """
        Возваращет список имен известных людей
        :return:
        """
        return self._known_face_names
