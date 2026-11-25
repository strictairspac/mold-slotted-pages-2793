import { api } from "../api/workbench.js";
import { errorText, field } from "../components/common/fields.js";
import { empty, pageHeading, section } from "../components/common/panel.js";
import { resultTable, table } from "../components/common/table.js";
import { submit } from "../hooks/submit.js";
import { el } from "../utils/dom.js";
import { cell, download, time } from "../utils/format.js";

function reviewForm(id, saved) {
  const form = el("form", {id: "review-form"},
    field("复核意见", el("textarea", {name: "note", required: true, minlength: 3, maxlength: 500, rows: 3})),
    errorText(), el("button", {type: "submit"}, "签署复核"));
  submit(form, async values => saved(await api.submitReview(id, {note: values.get("note")})));
  return form;
}

function signature(review) {
  return el("div", {"data-testid": "reviewed", class: "signature"},
    el("strong", {}, `已签署 · ${review.actor}`), el("p", {}, review.note), el("time", {}, time(review.created_at)));
}

function tracePanel(user, initialIndex) {
  const issue = errorText();
  const hits = el("div", {"aria-live": "polite"});
  const coverage = el("div", {});
  const input = el("input", {name: "key", maxlength: 24, placeholder: "履历号，如 GM-071"});
  let lastKey = "";

  async function search(key) {
    lastKey = key;
    issue.textContent = "";
    hits.replaceChildren(el("p", {class: "empty"}, "正在查询…"));
    try {
      const found = await api.trace(key);
      if (!found.length) {
        hits.replaceChildren(el("p", {class: "empty"},
          key ? `没有找到履历 ${key} 的追溯槽号。` : "还没有可追溯的批次。"));
        return;
      }
      hits.replaceChildren(table(["履历", "批次", "槽号", "备注", "参数", "完成时间"],
        found.map(hit => [hit.record_key, `#${hit.run_id} ${hit.case_title}`, hit.slot_id,
          hit.note, hit.parameter, time(hit.finished_at)]), "追溯地址表"));
    } catch (error) {
      hits.replaceChildren();
      issue.textContent = error.message;
    }
  }

  function coverageState(state) {
    if (!state) {
      coverage.replaceChildren();
      return;
    }
    if (state.complete) {
      coverage.replaceChildren(el("p", {class: "empty"}, "追溯地址表已覆盖全部已完成批次。"));
      return;
    }
    const run = el("button", {type: "button", onclick: async () => {
      run.disabled = true;
      issue.textContent = "";
      try {
        const result = await api.backfillTrace();
        coverageState(result);
        await search(lastKey);
      } catch (error) {
        issue.textContent = error.message;
      } finally {
        run.disabled = false;
      }
    }}, "继续回填");
    coverage.replaceChildren(el("div", {class: "trace-backfill"},
      el("p", {class: "empty"},
        `历史回填进行中：已有 ${state.indexed}/${state.total} 个批次入库，剩余 ${state.pending} 个批次也可直接查询。`),
      user.role === "operator" ? run : null));
  }

  const form = el("form", {class: "queue-form"},
    field("按履历号查最终槽号", input), el("button", {type: "submit"}, "查询"), issue);
  submit(form, values => search(values.get("key").trim()));
  search("");
  coverageState(initialIndex);
  return section("追溯地址表", form, coverage, hits);
}

export async function evidencePage(config, user, route) {
  const runs = (await api.runs()).filter(item => item.status === "done");
  const run = route.id ? await api.run(route.id) : runs[0];
  let indexState = null;
  try {
    indexState = await api.traceStatus();
  } catch {
    indexState = null;
  }
  const trace = tracePanel(user, indexState);
  if (!run?.result) return el("div", {class: "page"},
    pageHeading(config.modules[3], null), empty("成功执行一个批次后可以查看、签核和下载证据。"),
    trace, el("a", {href: "#runs"}, config.modules[2]));

  const review = await api.review(run.id);
  const issue = errorText();
  const button = el("button", {type: "button", onclick: async () => {
    button.disabled = true;
    issue.textContent = "";
    try {
      await download(await api.export(run.id), `evidence-${run.id}.json`);
    } catch (error) {
      issue.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  }}, "导出证据");
  const signing = el("div", {});
  signing.append(review ? signature(review) : user.role === "reviewer" ?
    reviewForm(run.id, data => signing.replaceChildren(signature(data))) : empty("待复核员签署。"));
  const options = el("select", {"aria-label": "选择已完成的批次", onchange: event => {
    location.hash = `evidence/${event.target.value}`;
  }}, runs.map(item => el("option", {value: item.id, selected: item.id === run.id}, `#${item.id} ${item.case_title}`)));
  return el("div", {class: "page evidence"},
    pageHeading(config.modules[3], run.case_title, button),
    issue, options, trace,
    el("section", {class: "feature evidence-summary"}, el("div", {}, el("h2", {}, "批次判定"), el("p", {}, run.result.summary)),
      el("details", {}, el("summary", {}, "证据摘要"), el("code", {}, run.digest))),
    el("dl", {class: "metrics"}, Object.entries(run.result.metrics).map(([label, value]) =>
      el("div", {}, el("dt", {}, label), el("dd", {}, cell(value))))),
    section("业务结果明细", run.result.rows.length ? resultTable(run.result.rows) : empty("此批次无明细。")),
    section("复核签署", signing));
}
