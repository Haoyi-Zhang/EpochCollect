"""Finite result-schema controls; no new campaign or timing measurements."""
import copy
from contextlib import contextmanager
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ART = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ART))
from verify_horizon import validate_row

REQUIRED = (('exhaustive', 'policy'), ('weighted', 'policy'),
            ('weighted', 'all_matchings'))
NON_MAPPINGS = (None, [], ['not-an-object'], '', 'not-an-object', 0, 1.5, True)


@contextmanager
def mutant_results(phase, field, missing):
    """Only mutate temporary copies of retained records, never the evidence."""
    with tempfile.TemporaryDirectory(prefix='phase-schema-') as tmp:
        directory = Path(tmp)
        for name in ('exhaustive', 'weighted', 'oracle', 'stress'):
            shutil.copy2(ART / 'results/horizon' / f'{name}.jsonl', directory)
        path = directory / f'{phase}.jsonl'
        lines = path.read_text(encoding='utf-8').splitlines()
        index = 40 if phase == 'weighted' else 0
        row = json.loads(lines[index])
        if missing:
            del row[field]
        else:
            row[field] = []
        lines[index] = json.dumps(row, separators=(',', ':'))
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        yield directory


class PhaseSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = {}
        for phase in ('exhaustive', 'weighted', 'oracle', 'stress'):
            index = 40 if phase == 'weighted' else 0
            raw = json.loads((ART / 'inputs' / f'horizon-{phase}.jsonl')
                             .read_text(encoding='utf-8').splitlines()[index])
            row = json.loads((ART / 'results/horizon' / f'{phase}.jsonl')
                             .read_text(encoding='utf-8').splitlines()[index])
            cls.fixtures[phase] = raw, row

    def reject(self, phase, field, value=None, missing=False):
        raw, original = self.fixtures[phase]
        row = copy.deepcopy(original)
        if missing:
            row.pop(field, None)
        else:
            row[field] = value
        with self.assertRaisesRegex(ValueError, f'{phase}.*{field}.*mapping'):
            validate_row(row, raw, phase)

    def test_valid_required_phase_rows(self):
        self.assertEqual(self.fixtures['weighted'][1]['case'], 'weighted0040')
        for phase in ('exhaustive', 'weighted'):
            raw, row = self.fixtures[phase]
            validate_row(row, raw, phase)

    def test_compact_oracle_and_stress_remain_legal(self):
        for phase in ('oracle', 'stress'):
            raw, row = self.fixtures[phase]
            self.assertNotIn('policy', row)
            self.assertNotIn('all_matchings', row)
            validate_row(row, raw, phase)
        raws = (ART / 'inputs/horizon-stress.jsonl').read_text(encoding='utf-8').splitlines()
        rows = (ART / 'results/horizon/stress.jsonl').read_text(encoding='utf-8').splitlines()
        incomplete = 0
        for raw, row in zip(map(json.loads, raws), map(json.loads, rows)):
            if any(row[alg]['status'] == 'incomplete' for alg in ('horizon', 'prefix')):
                validate_row(row, raw, 'stress')
                incomplete += 1
        self.assertGreater(incomplete, 0)

    def test_exhaustive_does_not_require_ablation(self):
        raw, row = self.fixtures['exhaustive']
        self.assertNotIn('all_matchings', row)
        validate_row(row, raw, 'exhaustive')

    def test_missing_required_policy(self):
        for phase in ('exhaustive', 'weighted'):
            with self.subTest(phase=phase):
                self.reject(phase, 'policy', missing=True)

    def test_missing_weighted_ablation(self):
        self.reject('weighted', 'all_matchings', missing=True)

    def test_nonmapping_required_fields(self):
        for phase, field in REQUIRED:
            for value in NON_MAPPINGS:
                with self.subTest(phase=phase, field=field, value=value):
                    self.reject(phase, field, value)

    def test_nonmapping_supplied_optional_fields(self):
        optional = [('exhaustive', 'all_matchings')] + [
            (phase, field) for phase in ('oracle', 'stress')
            for field in ('policy', 'all_matchings')]
        for phase, field in optional:
            for value in NON_MAPPINGS:
                with self.subTest(phase=phase, field=field, value=value):
                    self.reject(phase, field, value)

    def test_existing_ablation_content_gate_is_preserved(self):
        for phase in ('exhaustive', 'weighted', 'oracle', 'stress'):
            raw, original = self.fixtures[phase]
            row = copy.deepcopy(original)
            row['all_matchings'] = copy.deepcopy(row['horizon'])
            validate_row(row, raw, phase)
            row['all_matchings']['status'] = 'invalid'
            with self.assertRaisesRegex(ValueError, 'completion status'):
                validate_row(row, raw, phase)

    def test_existing_policy_content_gate_is_preserved(self):
        for phase in ('exhaustive', 'weighted'):
            raw, original = self.fixtures[phase]
            row = copy.deepcopy(original)
            row['policy']['max_ratio'] = '1000'
            with self.assertRaisesRegex(ValueError, 'policy price'):
                validate_row(row, raw, phase)

    def cli(self, *args):
        command = [sys.executable, '-B'] + ['-O'] * sys.flags.optimize
        return subprocess.run(command + list(map(str, args)), cwd=ART,
                              capture_output=True, text=True, encoding='utf-8', timeout=15)

    def check_verifier_cli(self, missing):
        for phase, field in REQUIRED:
            with self.subTest(phase=phase, field=field, missing=missing):
                with mutant_results(phase, field, missing) as directory:
                    p = self.cli(ART / 'verify_horizon.py', directory)
                    self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                    self.assertEqual(p.stdout, '')
                    self.assertRegex(p.stderr, f'verification failed: {phase}.*{field}.*mapping')

    def test_native_verifier_cli_missing_fields(self):
        self.check_verifier_cli(missing=True)

    def test_native_verifier_cli_wrong_types(self):
        self.check_verifier_cli(missing=False)

    def test_native_table_consumer_rejects_before_writes(self):
        for phase, field in REQUIRED:
            for missing in (True, False):
                with self.subTest(phase=phase, field=field, missing=missing):
                    with mutant_results(phase, field, missing) as directory:
                        output = directory / 'derived'
                        p = self.cli(ART / 'make_horizon_tables.py', '--results', directory,
                                     '--output-dir', output)
                        self.assertNotEqual(p.returncode, 0)
                        self.assertRegex(p.stderr, f'ValueError: {phase}.*{field}.*mapping')
                        self.assertNotIn('KeyError', p.stderr)
                        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
