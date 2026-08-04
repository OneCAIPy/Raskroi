from dataclasses import dataclass
from email.parser import BytesParser
from email.policy import default


@dataclass(frozen=True)
class UploadedFormFile:
	field_name: str
	filename: str
	content_type: str
	contents: bytes


class MultipartFormError(ValueError):
	pass


def read_uploaded_file(
	*,
	body: bytes,
	content_type: str,
	field_name: str,
) -> UploadedFormFile:
	if "\r" in content_type or "\n" in content_type:
		raise MultipartFormError("Некорректный заголовок загрузки файла.")
	if not content_type.lower().startswith("multipart/form-data"):
		raise MultipartFormError("Файл должен быть отправлен как multipart/form-data.")

	message = BytesParser(policy=default).parsebytes(
		f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
		+ body
	)
	if not message.is_multipart():
		raise MultipartFormError("Не удалось разобрать данные загруженного файла.")

	for part in message.iter_parts():
		if part.get_content_disposition() != "form-data":
			continue
		part_field_name = part.get_param("name", header="content-disposition")
		if part_field_name != field_name:
			continue
		filename = part.get_filename() or ""
		contents = part.get_payload(decode=True) or b""
		return UploadedFormFile(
			field_name=field_name,
			filename=filename,
			content_type=part.get_content_type(),
			contents=contents,
		)

	raise MultipartFormError("Выбери файл Excel формата .xlsx.")
