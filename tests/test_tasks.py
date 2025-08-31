from tasks import TaskType


def test_import_companies_task_type_exists():
    """Test that the new IMPORT_COMPANIES_FROM_SPREADSHEET task type exists and is recognized."""
    assert (
        TaskType.IMPORT_COMPANIES_FROM_SPREADSHEET.value
        == "import_companies_from_spreadsheet"
    )
    # Verify it can be instantiated from its string value
    assert (
        TaskType("import_companies_from_spreadsheet")
        == TaskType.IMPORT_COMPANIES_FROM_SPREADSHEET
    )


def test_merge_companies_task_type_exists():
    assert TaskType.MERGE_COMPANIES.value == "merge_companies"
    assert TaskType("merge_companies") == TaskType.MERGE_COMPANIES
