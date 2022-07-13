import pytest

from backend.worker import tasks


@pytest.mark.celery
class TestTasks:
    def test_fuzz(self, campaign_id, fuzzer, target, program, tmp_path):
        task = tasks.fuzz.apply_async(args=[campaign_id, fuzzer, target, program, 1, '10s'])
        report = task.get()
        assert report

    def test_start_campaign(self, campaign):
        campaign = campaign.dict(exclude_unset=True, exclude_none=True)
        task = tasks.start_campaign.apply_async(args=[campaign])
        chord_task_id = task.get()
        chord_result = tasks.app.AsyncResult(chord_task_id)
        chord_result.get()
