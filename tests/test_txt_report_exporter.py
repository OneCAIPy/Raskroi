from cutting_app.app.domain.cut_settings import CutSettings
from cutting_app.app.domain.edge import EdgeSet, EdgeSpec
from cutting_app.app.domain.part import PartInput
from cutting_app.app.domain.return_remnant import ReturnRemnantSettings
from cutting_app.app.domain.sheet import SheetInput
from cutting_app.app.exporters.txt_report_exporter import export_cutting_result_to_txt
from cutting_app.app.services.guillotine_optimizer import optimize_guillotine_cutting


def test_txt_report_uses_familiar_summary_order_and_utf8_bom() -> None:
	result = optimize_guillotine_cutting(
		parts=[
			PartInput(
				number="A1",
				name="Фасад",
				l_mm=400,
				w_mm=400,
				quantity=2,
				edges=EdgeSet(L1=EdgeSpec(thickness_mm=1, material_name="ABS белая")),
			),
		],
		sheets=[
			SheetInput(
				name="Дополнительный кусок 1",
				width_mm=500,
				height_mm=500,
				is_remnant=True,
			),
			SheetInput(name="Лист", width_mm=1000, height_mm=1000),
		],
		settings=CutSettings(kerf_width_mm=4),
		return_remnant_settings=ReturnRemnantSettings(
			min_long_side_mm=80,
			min_short_side_mm=80,
			min_area_mm2=1,
		),
	)

	report = export_cutting_result_to_txt(result)

	assert report.startswith("\ufeffКоличество плит материала\t1\r\n")
	assert "Количество использованных дополнительных кусков\t1\r\n" in report
	assert "Облицовка\tABS белая\r\n" in report
	assert "Количество панелей\t2\r\n" in report
	assert "Количество неразмещённых панелей\t0\r\n" in report
	assert "Обрезки\r\n" in report
	assert report.index("КИМ\t") < report.index("Длина резов (проходов)\t")
	assert report.index("Длина резов (проходов)\t") < report.index("Облицовка\t")
	assert report.index("Облицовка\t") < report.index("Количество карт раскроя\t")
	assert report.index("Количество карт раскроя\t") < report.index("Профиль возвратного остатка\t")
	assert "." not in report.split("КИМ\t", 1)[1].split("\r\n", 1)[0]


def test_txt_report_explicitly_reports_no_edge_material() -> None:
	result = optimize_guillotine_cutting(
		parts=[
			PartInput(
				number="A1",
				name="Полка",
				l_mm=400,
				w_mm=400,
				quantity=1,
				edges=EdgeSet(),
			),
		],
		sheets=[SheetInput(name="Лист", width_mm=1000, height_mm=1000)],
		settings=CutSettings(kerf_width_mm=4),
	)

	report = export_cutting_result_to_txt(result)

	assert "Облицовка\tНе задана\r\n" in report
	assert "Длина облицовки\t0,000 м.\r\n" in report
	assert "Количество отрезов облицовки\t0\r\n" in report
