from cutting_app.app.importers.manual_parts_text_importer import parse_manual_parts_text


def test_parse_manual_parts_text_creates_parts_with_empty_edges() -> None:
	result = parse_manual_parts_text(
		"A1; Боковина; 720; 500; 2\n"
		"A2; Полка; 680,5; 300; 3"
	)

	assert result.errors == []
	assert len(result.parts) == 2
	assert result.parts[0].number == "A1"
	assert result.parts[0].name == "Боковина"
	assert result.parts[0].l_mm == 720
	assert result.parts[0].w_mm == 500
	assert result.parts[0].quantity == 2
	assert not result.parts[0].edges.L1.has_edge
	assert result.parts[1].l_mm == 680.5


def test_parse_manual_parts_text_reports_line_errors() -> None:
	result = parse_manual_parts_text(
		"A1; Без количества; 720; 500\n"
		"A2; Полка; ширина; 300; 1\n"
		"A3; Цоколь; 680; 100; 0"
	)

	assert result.parts == []
	assert len(result.errors) == 3
	assert result.errors[0].line_number == 1
	assert "Ожидается 5 полей" in result.errors[0].message
	assert "Поле L должно быть числом" in result.errors[1].message
	assert "количество" in result.errors[2].message
