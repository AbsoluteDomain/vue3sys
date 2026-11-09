"""系统管理-审批流转单元测试。

覆盖审批配置匹配、通用审批拦截、审批决策（或签/会签/驳回/执行失败）
以及「审批通过后重放业务请求」的端到端执行链路。
"""
import json
from datetime import date
from unittest.mock import patch

from django.test import RequestFactory, TestCase

from apps.product.boms.models import BomList
from apps.product.boms.views import create_bom
from apps.product.production_plan.models import ProductionPlan
from apps.product.production_plan.views import save_production_plan
from apps.system.approval import services
from apps.system.approval.models import (
    ApprovalConfig,
    ApprovalRequest,
    ApprovalRequestApprover,
)
from apps.system.approval.views import (
    config_create,
    my_tasks,
    request_history,
    submit_request,
)
from apps.system.menus.models import Menu
from apps.system.operation_logs.views import approval_record_list
from apps.system.users.models import User


def make_request(user, path="/api/v1/bom/create/", method="POST", body=None, bypass=False):
    """构造一个已携带登录用户信息的请求。"""
    factory = RequestFactory()
    payload = json.dumps(body or {}, ensure_ascii=False)
    if method == "GET":
        request = factory.get(path, data=body or {})
    else:
        request = factory.generic(method, path, data=payload, content_type="application/json")
    if user:
        request.META["_JWT_PAYLOAD"] = {
            "user_id": user.id,
            "user_name": user.username,
            "nickname": user.nickname or user.username,
        }
    request._approval_bypass = bypass
    return request


class ApprovalTestBase(TestCase):
    """公共测试数据：两名审核人 + 一名申请人。"""

    @classmethod
    def setUpTestData(cls):
        cls.applicant = User.objects.create_user(username="t_applicant", nickname="申请人")
        cls.approver1 = User.objects.create_user(username="t_approver1", nickname="审核人1")
        cls.approver2 = User.objects.create_user(username="t_approver2", nickname="审核人2")

    def make_config(self, perm_code, biz_type=None, enabled=1, mode="single", approver_ids=None):
        return ApprovalConfig.objects.create(
            biz_type=biz_type or perm_code,
            perm_code=perm_code,
            name=f"测试审批-{perm_code}",
            enabled=enabled,
            approval_mode=mode,
            approver_ids=approver_ids if approver_ids is not None else str(self.approver1.id),
            approver_names="审核人1",
        )


class ActiveConfigTests(ApprovalTestBase):
    def test_enabled_config_is_returned_by_perm(self):
        config = self.make_config("product:bom:create")
        self.assertEqual(services.get_active_config_by_perm("product:bom:create"), config)

    def test_disabled_config_returns_none(self):
        self.make_config("product:bom:create", enabled=0)
        self.assertIsNone(services.get_active_config_by_perm("product:bom:create"))

    def test_unknown_perm_returns_none(self):
        self.assertIsNone(services.get_active_config_by_perm("product:not-exists"))

    def test_stock_config_biz_type_falls_back_to_perm(self):
        """历史配置行把 perm_code 写入 biz_type 时，出入库接口仍能匹配到。"""
        config = self.make_config("product:stock:inbound")

        self.assertEqual(services.get_active_config("inbound"), config)


class MaybeSubmitApprovalTests(ApprovalTestBase):
    def test_perm_outside_whitelist_is_ignored(self):
        """白名单之外的权限不允许走审批通道，防止越权提交。"""
        self.make_config("product:bom:create")
        request = make_request(self.applicant, body={"approval_perm": "product:bom:create"})

        result = services.maybe_submit_approval(
            request, "product:bom:create", {"product:bom:update"},
            target_id=1, target_name="BOM",
        )

        self.assertIsNone(result)
        self.assertEqual(ApprovalRequest.objects.count(), 0)

    def test_missing_perm_is_ignored(self):
        self.make_config("product:bom:create")
        request = make_request(self.applicant, body={})

        result = services.maybe_submit_approval(
            request, None, {"product:bom:create"}, target_id=1, target_name="BOM",
        )

        self.assertIsNone(result)

    def test_disabled_config_is_ignored(self):
        self.make_config("product:bom:create", enabled=0)
        request = make_request(self.applicant, body={"approval_perm": "product:bom:create"})

        result = services.maybe_submit_approval(
            request, "product:bom:create", {"product:bom:create"},
            target_id=1, target_name="BOM",
        )

        self.assertIsNone(result)

    def test_enabled_config_creates_pending_request(self):
        self.make_config("product:bom:create")
        body = {"bom_model": "TEST-BOM-1", "approval_perm": "product:bom:create"}
        request = make_request(self.applicant, body=body)

        approval = services.maybe_submit_approval(
            request, "product:bom:create", {"product:bom:create"},
            target_id=None, target_name="TEST-BOM-1", summary="新增BOM：TEST-BOM-1",
        )

        self.assertIsNotNone(approval)
        self.assertEqual(approval.status, ApprovalRequest.STATUS_PENDING)
        self.assertEqual(approval.target_id, 0)  # 新增类业务无主键时落 0
        self.assertEqual(approval.applicant_id, self.applicant.id)
        self.assertEqual(approval.applicant_name, "申请人")
        self.assertEqual(approval.approval_mode, "single")

        # 审批通过后重放用的步骤
        payload = json.loads(approval.payload)
        self.assertEqual(payload["perm_code"], "product:bom:create")
        self.assertEqual(len(payload["steps"]), 1)
        self.assertEqual(payload["steps"][0]["path"], request.path)
        self.assertEqual(payload["steps"][0]["method"], "POST")
        self.assertEqual(payload["steps"][0]["body"], body)

        approvers = list(approval.approvers.all())
        self.assertEqual(len(approvers), 1)
        self.assertEqual(approvers[0].approver_id, self.approver1.id)
        self.assertEqual(approvers[0].decision, ApprovalRequestApprover.DECISION_PENDING)

    def test_invalid_approvers_do_not_block_business(self):
        """配置里的审核人全部失效时，不创建审批单，业务照常执行。"""
        self.make_config("product:bom:create", approver_ids="999999")
        request = make_request(self.applicant, body={"approval_perm": "product:bom:create"})

        result = services.maybe_submit_approval(
            request, "product:bom:create", {"product:bom:create"},
            target_id=1, target_name="BOM",
        )

        self.assertIsNone(result)
        self.assertEqual(ApprovalRequest.objects.count(), 0)

    def test_replay_request_skips_approval(self):
        """审批通过后重放的请求必须跳过审批，避免二次生成申请单。"""
        self.make_config("product:bom:create")
        request = make_request(self.applicant, body={"approval_perm": "product:bom:create"}, bypass=True)

        result = services.maybe_submit_approval(
            request, "product:bom:create", {"product:bom:create"},
            target_id=1, target_name="BOM",
        )

        self.assertIsNone(result)
        self.assertEqual(ApprovalRequest.objects.count(), 0)


class DecideRequestTests(ApprovalTestBase):
    def create_pending_request(self, mode="single", approver_ids=None, steps=None):
        config = self.make_config(
            "product:bom:create",
            mode=mode,
            approver_ids=approver_ids if approver_ids is not None else str(self.approver1.id),
        )
        request = make_request(self.applicant, body={"approval_perm": "product:bom:create"})
        return services.create_approval_request(
            request,
            config,
            "product:bom:create",
            target_id=1,
            target_name="TEST-BOM-1",
            summary="测试审批",
            steps=steps if steps is not None else [],
        )

    def decide(self, user, request_id, decision=ApprovalRequestApprover.DECISION_APPROVED, comment="ok"):
        request = make_request(user, path=f"/api/v1/approvals/requests/{request_id}/approve")
        return services.decide_request(request, request_id, decision, comment)

    def test_single_mode_any_approver_passes(self):
        config = self.make_config(
            "product:bom:create",
            approver_ids=f"{self.approver1.id},{self.approver2.id}",
        )
        approval = services.create_approval_request(
            make_request(self.applicant, body={}), config, "product:bom:create",
            target_id=1, target_name="BOM", summary="审批", steps=[],
        )

        with patch.object(services, "_execute_request", return_value=(True, "")) as executor:
            result, message = self.decide(self.approver1, approval.id)

        approval.refresh_from_db()
        self.assertEqual(approval.status, ApprovalRequest.STATUS_APPROVED)
        self.assertEqual(message, "审批已通过，业务已执行")
        executor.assert_called_once()

    def test_reject_marks_rejected_without_execution(self):
        approval = self.create_pending_request()

        with patch.object(services, "_execute_request", return_value=(True, "")) as executor:
            result, message = self.decide(
                self.approver1, approval.id, ApprovalRequestApprover.DECISION_REJECTED, "不同意",
            )

        approval.refresh_from_db()
        self.assertEqual(approval.status, ApprovalRequest.STATUS_REJECTED)
        self.assertEqual(message, "已驳回该审批")
        executor.assert_not_called()
        self.assertIsNotNone(approval.finished_at)

    def test_multi_mode_requires_all_approvers(self):
        approval = self.create_pending_request(
            mode="multi",
            approver_ids=f"{self.approver1.id},{self.approver2.id}",
        )

        with patch.object(services, "_execute_request", return_value=(True, "")) as executor:
            _result, first_message = self.decide(self.approver1, approval.id)
            approval.refresh_from_db()
            self.assertEqual(approval.status, ApprovalRequest.STATUS_PENDING)
            self.assertIn("剩余 1 人", first_message)
            executor.assert_not_called()

            _result, second_message = self.decide(self.approver2, approval.id)

        approval.refresh_from_db()
        self.assertEqual(approval.status, ApprovalRequest.STATUS_APPROVED)
        self.assertEqual(second_message, "审批已通过，业务已执行")
        executor.assert_called_once()

    def test_multi_mode_one_reject_stops_flow(self):
        approval = self.create_pending_request(
            mode="multi",
            approver_ids=f"{self.approver1.id},{self.approver2.id}",
        )
        self.decide(self.approver1, approval.id, ApprovalRequestApprover.DECISION_REJECTED, "不同意")
        approval.refresh_from_db()
        self.assertEqual(approval.status, ApprovalRequest.STATUS_REJECTED)

        # 已驳回后其他审核人不能再处理
        with self.assertRaisesMessage(ValueError, "该审批已处理"):
            self.decide(self.approver2, approval.id)

    def test_non_approver_cannot_decide(self):
        approval = self.create_pending_request()
        other = User.objects.create_user(username="t_other", nickname="路人")

        with self.assertRaisesMessage(ValueError, "您不是该审批的待处理审核人"):
            self.decide(other, approval.id)

    def test_decide_requires_operator(self):
        approval = self.create_pending_request()
        request = RequestFactory().post(f"/api/v1/approvals/requests/{approval.id}/approve", data="{}",
                                        content_type="application/json")

        with self.assertRaisesMessage(ValueError, "无法识别当前操作人"):
            services.decide_request(request, approval.id, ApprovalRequestApprover.DECISION_APPROVED)

    def test_execution_failure_marks_request_failed(self):
        """无法解析的重放地址会执行失败，但审批状态需落库记录原因。"""
        approval = self.create_pending_request(
            steps=[{"path": "/api/v1/__not_exists__/", "method": "POST", "body": {}}],
        )

        _result, message = self.decide(self.approver1, approval.id)

        approval.refresh_from_db()
        self.assertEqual(approval.status, ApprovalRequest.STATUS_FAILED)
        self.assertTrue(approval.execute_error)
        self.assertIn("业务执行失败", message)


class ReplayExecutionTests(ApprovalTestBase):
    """审批通过后按申请人身份重放原始业务请求。"""

    def test_bom_create_intercept_then_execute(self):
        config = self.make_config("product:bom:create")
        body = {
            "bom_model": "TEST-REPLAY-BOM",
            "bom_name": "重放测试BOM",
            "material_code": "TEST-REPLAY-MC",
            "type": 0,
            "recipes": [],
            "approval_perm": "product:bom:create",
        }
        request = make_request(self.applicant, body=body)

        response = create_bom(request)
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(data["code"], "00000")
        self.assertTrue(data["data"]["pending"])
        self.assertEqual(BomList.objects.filter(bom_model="TEST-REPLAY-BOM").count(), 0)

        request_id = data["data"]["request_id"]
        services.decide_request(
            make_request(self.approver1), request_id, ApprovalRequestApprover.DECISION_APPROVED,
        )

        bom = BomList.objects.filter(bom_model="TEST-REPLAY-BOM", is_del=0).first()
        self.assertIsNotNone(bom)
        self.assertEqual(bom.bom_name, "重放测试BOM")
        approval = ApprovalRequest.objects.get(id=request_id)
        self.assertEqual(approval.status, ApprovalRequest.STATUS_APPROVED)

    def test_production_plan_save_intercept_then_execute(self):
        bom = BomList.objects.create(
            bom_model="TEST-PLAN-BOM", bom_name="计划测试BOM",
            material_code="TEST-PLAN-MC", type=0, is_del=0,
        )
        plan_date = date(2027, 12, 31)
        ProductionPlan.objects.create(plan_date=plan_date, bom_id=bom.id, quantity=3)
        self.make_config("production:plan:save")

        body = {
            "date": plan_date.strftime("%Y-%m-%d"),
            "boms": [],
            "multiplier": 1.5,
            "approval_perm": "production:plan:save",
        }
        response = save_production_plan(make_request(
            self.applicant, path="/api/v1/production-plan/save", body=body,
        ))

        data = json.loads(response.content.decode("utf-8"))
        self.assertTrue(data["data"]["pending"])
        # 提交审批时不能清空原计划
        self.assertEqual(ProductionPlan.objects.filter(plan_date=plan_date).count(), 1)

        request_id = data["data"]["request_id"]
        services.decide_request(
            make_request(self.approver1), request_id, ApprovalRequestApprover.DECISION_APPROVED,
        )

        self.assertEqual(ProductionPlan.objects.filter(plan_date=plan_date).count(), 0)
        self.assertEqual(
            ApprovalRequest.objects.get(id=request_id).status, ApprovalRequest.STATUS_APPROVED,
        )


class PendingCountTests(ApprovalTestBase):
    def test_pending_count_only_counts_my_pending_tasks(self):
        config = self.make_config(
            "product:bom:create", approver_ids=f"{self.approver1.id},{self.approver2.id}",
        )
        approval = services.create_approval_request(
            make_request(self.applicant, body={}), config, "product:bom:create",
            target_id=1, target_name="BOM", summary="审批", steps=[],
        )

        self.assertEqual(services.pending_count(self.approver1.id), 1)
        self.assertEqual(services.pending_count(self.approver2.id), 1)
        self.assertEqual(services.pending_count(self.applicant.id), 0)

        with patch.object(services, "_execute_request", return_value=(True, "")):
            services.decide_request(
                make_request(self.approver1), approval.id, ApprovalRequestApprover.DECISION_APPROVED,
            )
        self.assertEqual(services.pending_count(self.approver1.id), 0)
        self.assertEqual(services.pending_count(self.approver2.id), 0)


class ApprovalRecordListTests(ApprovalTestBase):
    """审批记录接口：按动作逐条输出完整审批链路。"""

    def setUp(self):
        self.config = self.make_config("product:bom:create")

    def create_request(self, target_name, summary):
        return services.create_approval_request(
            make_request(self.applicant, body={}), self.config, "product:bom:create",
            target_id=1, target_name=target_name, summary=summary, steps=[],
        )

    def fetch(self, params=None):
        request = RequestFactory().get("/api/v1/operation-logs/approval-records/", params or {})
        response = approval_record_list(request)
        return json.loads(response.content.decode("utf-8"))

    def test_list_expands_each_request_into_full_events(self):
        pending = self.create_request("BOM-A", "申请A")
        approved = self.create_request("BOM-B", "申请B")
        with patch.object(services, "_execute_request", return_value=(True, "")):
            services.decide_request(
                make_request(self.approver1), approved.id,
                ApprovalRequestApprover.DECISION_APPROVED, "同意执行",
            )

        data = self.fetch()["data"]

        # 待审批：提交 1 条；已通过：提交 + 同意 + 执行成功 3 条
        self.assertEqual(data["total"], 4)
        types = [item["type"] for item in data["list"]]
        self.assertEqual(types.count("submit"), 2)
        self.assertEqual(types.count("approve"), 1)
        self.assertEqual(types.count("execute"), 1)

        approve_row = next(item for item in data["list"] if item["type"] == "approve")
        self.assertEqual(approve_row["requestId"], approved.id)
        self.assertEqual(approve_row["actor"], "审核人1")
        self.assertEqual(approve_row["typeName"], "同意")
        self.assertEqual(approve_row["detail"], "同意执行")

        execute_row = next(item for item in data["list"] if item["type"] == "execute")
        self.assertEqual(execute_row["actor"], "系统")
        self.assertEqual(execute_row["typeName"], "业务执行成功")

        pending_submits = [
            item for item in data["list"]
            if item["type"] == "submit" and item["requestId"] == pending.id
        ]
        self.assertEqual(len(pending_submits), 1)

    def test_filter_by_event_type(self):
        self.create_request("BOM-A", "申请A")
        self.create_request("BOM-B", "申请B")

        data = self.fetch({"eventType": "submit"})["data"]

        self.assertEqual(data["total"], 2)
        self.assertTrue(all(item["type"] == "submit" for item in data["list"]))

    def test_filter_by_actor_keyword_and_date(self):
        self.create_request("BOM-A", "申请A")
        approved = self.create_request("BOM-B", "申请B")
        with patch.object(services, "_execute_request", return_value=(True, "")):
            services.decide_request(
                make_request(self.approver1), approved.id,
                ApprovalRequestApprover.DECISION_APPROVED,
            )

        # 审核人只命中已处理的同意动作
        self.assertEqual(self.fetch({"userName": "审核人1"})["data"]["total"], 1)
        # 申请人命中两条提交记录
        self.assertEqual(self.fetch({"userName": "申请人"})["data"]["total"], 2)
        # 关键词命中业务对象
        self.assertEqual(self.fetch({"keyword": "BOM-A"})["data"]["total"], 1)
        # 非法日期不报错，按未传处理
        self.assertEqual(self.fetch({"startTime": "not-a-date"})["data"]["total"], 4)

    def test_reject_event_recorded(self):
        rejected = self.create_request("BOM-C", "申请C")
        services.decide_request(
            make_request(self.approver1), rejected.id,
            ApprovalRequestApprover.DECISION_REJECTED, "资料不完整",
        )

        rows = self.fetch({"eventType": "reject"})["data"]["list"]

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["requestId"], rejected.id)
        self.assertEqual(rows[0]["actor"], "审核人1")
        self.assertEqual(rows[0]["detail"], "资料不完整")
        self.assertEqual(rows[0]["statusName"], "已驳回")

    def test_execute_failed_event_recorded(self):
        failed = services.create_approval_request(
            make_request(self.applicant, body={}), self.config, "product:bom:create",
            target_id=1, target_name="BOM-D", summary="申请D",
            steps=[{"path": "/api/v1/__not_exists__/", "method": "POST", "body": {}}],
        )
        services.decide_request(
            make_request(self.approver1), failed.id,
            ApprovalRequestApprover.DECISION_APPROVED,
        )

        rows = self.fetch({"eventType": "execute_failed"})["data"]["list"]

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["requestId"], failed.id)
        self.assertEqual(rows[0]["typeName"], "业务执行失败")
        self.assertTrue(rows[0]["detail"])


class ApprovalHistoryTests(ApprovalTestBase):
    """我已处理的列表与单申请审批历史。"""

    def setUp(self):
        self.config = self.make_config("product:bom:create")

    def create_request(self, target_name):
        return services.create_approval_request(
            make_request(self.applicant, body={}), self.config, "product:bom:create",
            target_id=1, target_name=target_name, summary=f"申请{target_name}", steps=[],
        )

    def test_processed_scope_only_returns_decided_requests(self):
        self.create_request("BOM-A")
        approved = self.create_request("BOM-B")
        with patch.object(services, "_execute_request", return_value=(True, "")):
            services.decide_request(
                make_request(self.approver1), approved.id,
                ApprovalRequestApprover.DECISION_APPROVED,
            )

        request = make_request(
            self.approver1, path="/api/v1/approvals/my-tasks",
            method="GET", body={"scope": "processed", "pageNum": 1, "pageSize": 10},
        )
        data = json.loads(my_tasks(request).content.decode("utf-8"))["data"]

        self.assertEqual(data["total"], 1)
        self.assertEqual(data["list"][0]["id"], approved.id)
        self.assertEqual(data["list"][0]["my_decision"], 1)

    def test_history_returns_timeline_for_request(self):
        approval = self.create_request("BOM-A")
        with patch.object(services, "_execute_request", return_value=(True, "")):
            services.decide_request(
                make_request(self.approver1), approval.id,
                ApprovalRequestApprover.DECISION_APPROVED, "同意执行",
            )

        data = json.loads(
            request_history(make_request(self.approver1, method="GET"), approval.id).content.decode("utf-8")
        )["data"]

        self.assertEqual([item["type"] for item in data["events"]], ["submit", "approve", "execute"])
        self.assertEqual(data["events"][0]["actor"], "申请人")
        self.assertEqual(data["events"][1]["detail"], "同意执行")
        self.assertEqual(data["status_name"], "已通过")

    def test_mine_scope_only_returns_my_applications(self):
        mine = self.create_request("BOM-A")
        other = User.objects.create_user(username="t_applicant2", nickname="申请人2")
        services.create_approval_request(
            make_request(other, body={}), self.config, "product:bom:create",
            target_id=1, target_name="BOM-B", summary="申请B", steps=[],
        )

        data = json.loads(
            my_tasks(make_request(
                self.applicant, path="/api/v1/approvals/my-tasks",
                method="GET", body={"scope": "mine", "pageNum": 1, "pageSize": 10},
            )).content.decode("utf-8")
        )["data"]

        self.assertEqual(data["total"], 1)
        self.assertEqual(data["list"][0]["id"], mine.id)

    def test_history_not_found_returns_404(self):
        response = request_history(make_request(self.approver1, method="GET"), 999999)
        body = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(body["code"], "A0400")


class ApprovalSubmitApiTests(ApprovalTestBase):
    """通用审批提交接口：重放地址白名单校验与申请单创建。"""

    def setUp(self):
        self.make_config("product:bom:create")

    def submit(self, body):
        return json.loads(
            submit_request(
                make_request(self.applicant, path="/api/v1/approvals/requests", body=body)
            ).content.decode("utf-8")
        )

    def test_allowed_path_creates_pending_request(self):
        data = self.submit({
            "perm_code": "product:bom:create",
            "steps": [{"path": "/api/v1/bom/create/", "method": "POST", "body": {"bom_model": "X"}}],
            "target_name": "批量BOM",
        })

        self.assertEqual(data["code"], "00000")
        self.assertTrue(data["data"]["pending"])
        self.assertEqual(ApprovalRequest.objects.count(), 1)

    def test_path_outside_whitelist_is_rejected(self):
        data = self.submit({
            "perm_code": "product:bom:create",
            "steps": [{"path": "/api/v1/users/delete/", "method": "POST", "body": {}}],
        })

        self.assertEqual(data["code"], "A0400")
        self.assertEqual(ApprovalRequest.objects.count(), 0)


class ApprovalConfigCreateTests(ApprovalTestBase):
    """按钮权限首次保存审核配置（配置行尚不存在时创建）。"""

    def setUp(self):
        self.button = Menu.objects.create(
            parent_id=0, tree_path="0", name="库存-新增", type="B",
            perm="product:stock:create", visible=1, sort=0,
        )

    def create_config(self, body=None):
        payload = {
            "perm_code": "product:stock:create",
            "menu_id": self.button.id,
            "name": self.button.name,
            "enabled": 1,
            "approval_mode": "single",
            "approver_ids": [self.approver1.id],
        }
        payload.update(body or {})
        return json.loads(
            config_create(make_request(self.applicant, body=payload)).content.decode("utf-8")
        )

    def test_create_config_when_not_exists(self):
        data = self.create_config()

        self.assertEqual(data["code"], "00000")
        self.assertEqual(data["data"]["approver_names"], "审核人1")
        config = ApprovalConfig.objects.get(perm_code="product:stock:create")
        self.assertEqual(config.biz_type, "product:stock:create")
        self.assertEqual(config.enabled, 1)

    def test_save_again_reuses_existing_row(self):
        self.create_config()
        data = self.create_config({"enabled": 0, "approver_ids": []})

        self.assertEqual(data["code"], "00000")
        self.assertEqual(ApprovalConfig.objects.count(), 1)
        self.assertEqual(ApprovalConfig.objects.get().enabled, 0)

    def test_perm_code_must_match_menu(self):
        data = self.create_config({"perm_code": "product:stock:delete"})

        self.assertEqual(data["code"], "A0400")
        self.assertEqual(ApprovalConfig.objects.count(), 0)

    def test_inbound_perm_creates_biz_type_inbound(self):
        """出入库配置的 biz_type 必须写成 inbound/outbound，否则业务接口识别不到。"""
        button = Menu.objects.create(
            parent_id=0, tree_path="0", name="入库", type="B",
            perm="product:stock:inbound", visible=1, sort=0,
        )
        data = self.create_config(
            {"perm_code": "product:stock:inbound", "menu_id": button.id, "name": button.name}
        )

        self.assertEqual(data["code"], "00000")
        self.assertEqual(
            ApprovalConfig.objects.get(perm_code="product:stock:inbound").biz_type, "inbound"
        )
