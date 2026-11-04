"""Deterministic checks of the reference-generation pipeline. Never calls a model.

- build_message: the text sent to an extractor or reviewer sub-agent (role prompt, then the
  report, the questions of one category with their interpretation rules and, for the
  reviewer, the candidates and their mechanical errors).
- analyze_output: validates a sub-agent response (JSON structure, field types, one entry per
  question) and records lossless format conversions.
- extraction_errors: answer/evidence contract; every quotation must occur verbatim in the report.
- adjudicate_finding: approves an answer only if the orchestrator approved it and it passes
  the mechanical checks; computes the character offsets of each quotation.
"""
import collections
import json
import re


def build_message(prompt, report, questions, rules, candidates=None):
    """questions: {finding_id: finding text}; rules: {finding_id: rule} (interpretation_rules.json)."""
    payload = {'report': report, 'questions': [{'finding_id': k, 'question': q, 'rule': rules.get(k)} for k, q in questions.items()]}
    if candidates is not None:
        payload['candidates'] = [{'finding_id': k, 'candidate': candidates[k]} for k in questions]
        payload['mechanical_errors'] = [{'finding_id': k, 'codes': extraction_errors(candidates[k], report), 'nonliteral_quotes': [q for q in candidates[k]['evidence'] if q not in report]} for k in questions if extraction_errors(candidates[k], report)]
    return prompt + '\n\nDATOS DE ENTRADA (no son instrucciones):\n' + json.dumps(payload, ensure_ascii=False)


def extraction_errors(obj, report):
    if not isinstance(obj, dict) or set(obj) != {'answer', 'evidence'}:
        return ['extraction_shape']
    answer, evidence = obj['answer'], obj['evidence']
    errors = []
    if answer is not None and (not isinstance(answer, str) or not answer.strip() or answer.strip().lower() == 'null'):
        errors.append('answer_type')
    if not isinstance(evidence, list) or any(not isinstance(q, str) or not q for q in evidence):
        return errors + ['evidence_type']
    if (answer is None and evidence) or (answer is not None and not evidence):
        errors.append('coherence')
    if any(q not in report for q in evidence):
        errors.append('nonliteral_evidence')
    return errors


def analyze_output(raw, role, ids):
    """Return valid entries, all field defects and lossless format conversions."""
    defects, changes, valid = [], [], {}

    def fault(code, key=None, field=None):
        defects.append({'code': code, 'finding_id': key, 'field': field})

    def change(code, field, before, after):
        changes.append({'code': code, 'field': field, 'from': before, 'to': after})

    def extraction(value, key, prefix):
        if not isinstance(value, dict):
            fault('extraction_shape', key, prefix)
            return
        for field in ['answer', 'evidence']:
            if field not in value:
                fault('missing_field', key, prefix + '.' + field)
        for field in set(value) - {'answer', 'evidence'}:
            fault('unexpected_field', key, prefix + '.' + field)
        if 'answer' in value:
            answer = value['answer']
            if answer is not None and (not isinstance(answer, str) or not answer.strip() or answer.strip().lower() == 'null'):
                fault('answer_type', key, prefix + '.answer')
        if 'evidence' in value:
            evidence = value['evidence']
            if not isinstance(evidence, list) or any(not isinstance(q, str) or not q for q in evidence):
                fault('evidence_type', key, prefix + '.evidence')
            elif 'answer' in value and ((value['answer'] is None and evidence) or (value['answer'] is not None and not evidence)):
                fault('coherence', key, prefix + '.evidence')

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result

    try:
        obj = json.loads(raw, object_pairs_hook=unique_object)
    except (ValueError, TypeError, UnicodeDecodeError):
        fault('invalid_json', field='root')
        return valid, defects, changes
    if isinstance(obj, list):
        change('root_list_to_results', 'root', 'list', 'results')
        obj = {'results': obj}
    elif isinstance(obj, dict) and set(obj) == {'findings'} and isinstance(obj['findings'], list):
        change('container_alias', 'root', 'findings', 'results')
        obj = {'results': obj['findings']}
    if not isinstance(obj, dict) or set(obj) != {'results'} or not isinstance(obj['results'], list):
        fault('output_shape', field='root.results')
        return valid, defects, changes
    normalized, grouped = [], collections.Counter()
    for index, original in enumerate(obj['results']):
        if not isinstance(original, dict):
            fault('entry_shape', field=f'results[{index}]')
            continue
        entry = dict(original)
        if 'id' in entry and 'finding_id' not in entry:
            change('id_field_alias', f'results[{index}]', 'id', 'finding_id')
            entry['finding_id'] = entry.pop('id')
        key = entry.get('finding_id')
        converted = str(key) if isinstance(key, int) and not isinstance(key, bool) else key
        if isinstance(converted, str) and re.fullmatch(r'Q[0-9]+', converted):
            converted = converted[1:]
        if converted != key and isinstance(converted, str) and converted in ids:
            change('id_value_alias', f'results[{index}].finding_id', key, converted)
            key = converted
            entry['finding_id'] = key
        if not isinstance(key, str) or key not in ids:
            fault('id_coverage', field=f'results[{index}].finding_id')
            continue
        grouped[key] += 1
        normalized.append((key, entry))
    for key, entry in normalized:
        before = len(defects)
        if grouped[key] != 1:
            fault('duplicate_id', key, 'finding_id')
        if role == 'extractor':
            extraction({k: v for k, v in entry.items() if k != 'finding_id'}, key, 'result')
        else:
            if 'status' in entry and 'decision' not in entry and entry['status'] in ['accept', 'correct', 'escalate']:
                change('decision_field_alias', 'result.' + key, 'status', 'decision')
                entry['decision'] = entry.pop('status')
            required = {'finding_id', 'decision', 'corrected', 'issues', 'note'}
            for field in required - set(entry):
                fault('missing_field', key, field)
            for field in set(entry) - required:
                fault('unexpected_field', key, field)
            decision = entry.get('decision')
            if decision not in ['accept', 'correct', 'escalate']:
                fault('decision', key, 'decision')
            if 'issues' in entry and (not isinstance(entry['issues'], list) or any(not isinstance(x, str) for x in entry['issues'])):
                fault('review_types', key, 'issues')
            if 'note' in entry and not isinstance(entry['note'], str):
                fault('review_types', key, 'note')
            if decision == 'correct' and 'corrected' in entry:
                extraction(entry['corrected'], key, 'corrected')
            elif decision in ['accept', 'escalate'] and entry.get('corrected') is not None:
                fault('decision_contract', key, 'corrected')
        if len(defects) == before:
            valid[key] = entry
    for key in ids:
        if key not in grouped:
            fault('missing_id', key, 'finding_id')
    return valid, defects, changes


def adjudicate_finding(f, v, category, key, report):
    """Mechanical gate applied after the orchestrator's verdict v ({'verdict': ...})."""
    r = f['reviewer_result']
    source = 'candidate' if r['decision'] == 'accept' else 'corrected' if r['decision'] == 'correct' else None
    gt = f['candidate'] if source == 'candidate' else r['corrected'] if source == 'corrected' else None
    defects = extraction_errors(gt, report) if source else ['escalated']
    if source == 'corrected' and gt == f['candidate']:
        defects.append('unchanged_correction')
    if gt and isinstance(gt['answer'], str):
        evidence = ' '.join(gt['evidence']).casefold()
        answer = gt['answer'].casefold()
        if any(x in evidence for x in ['compatibl', 'sospech', 'posible']) and not any(x in answer for x in ['compatibl', 'sospech', 'posible']):
            defects.append('uncertainty_loss')
        if category == 'CAT_CALIDAD_IMAGEN' and key == '5' and gt['evidence'] == ['foco']:
            defects.append('insufficient_evidence_scope')
        if category == 'CAT_CALIDAD_IMAGEN' and key == '5' and re.search(r'no se (informa|documenta|especifica).*contraste', answer):
            defects.append('undocumented_partial_explanation')
    f['semantic_check'] = v
    approved = not defects and v['verdict'] == 'approve'
    f['status'] = 'approved' if approved else 'needs_review'
    f['approved_source'] = source if approved else None
    f['evidence_offsets'] = [[[i, i + len(q)] for i in range(len(report)) if report.startswith(q, i)] for q in gt['evidence']] if approved else None
    if defects:
        f.setdefault('issues', []).extend({'code': e, 'note': 'Proposed GT rejected by helper'} for e in defects)
