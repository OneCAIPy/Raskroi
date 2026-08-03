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
	assert "Ожидается 5 или 9 полей" in result.errors[0].message
	assert "Поле L должно быть числом" in result.errors[1].message
	assert "количество" in result.errors[2].message


def test_parse_manual_parts_text_reads_edges_from_extended_format() -> None:
	result = parse_manual_parts_text(
		"A1; Фасад; 300; 800; 1; "
		"1|0,5|10|ABS белая; "
		"1; "
		"2|0|20|ABS графит; -"
	)

	assert result.errors == []
	assert len(result.parts) == 1
	part = result.parts[0]
	assert part.edges.L1.thickness_mm == 1
	assert part.edges.L1.trimming_allowance_mm == 0.5
	assert part.edges.L1.tape_overhang_mm == 10
	assert part.edges.L1.material_name == "ABS белая"
	assert part.edges.L2.thickness_mm == 1
	assert part.edges.L2.trimming_allowance_mm == 0
	assert part.edges.L2.tape_overhang_mm == 0
	assert part.edges.L2.material_name == ""
	assert part.edges.W1.thickness_mm == 2
	assert part.edges.W1.tape_overhang_mm == 20
	assert part.edges.W1.material_name == "ABS графит"
	assert not part.edges.W2.has_edge


def test_parse_manual_parts_text_reports_edge_parameter_errors() -> None:
	result = parse_manual_parts_text(
		"A1; Фасад; 300; 800; 1; "
		"1|-0,5|0|ABS; broken|edge|value|with|extra; -; -"
	)

	assert result.parts == []
	assert len(result.errors) == 1
	assert "Кромка L1" in result.errors[0].message
	assert "прифуговка" in result.errors[0].message
	assert "Кромка L2" in result.errors[0].message
	assert "не более 4 параметров" in result.errors[0].message


def test_parse_manual_parts_text_rejects_edge_that_makes_size_invalid() -> None:
	result = parse_manual_parts_text(
		"A1; Узкая деталь; 1; 100; 1; -; -; 1|0|0|ABS; 1|0|0|ABS"
	)

	assert result.parts == []
	assert len(result.errors) == 1
	assert "Размер L без кромки должен быть больше 0" in result.errors[0].message
