import type { Reporter, TestModule } from 'vitest/node'

const SLOWEST_COUNT = 10

export default class SlowestTestsReporter implements Reporter {
  onTestRunEnd(testModules: ReadonlyArray<TestModule>) {
    const durations = testModules
      .flatMap((testModule) => [...testModule.children.allTests()])
      .map((test) => ({ name: test.fullName, duration: test.diagnostic()?.duration ?? 0 }))
      .sort((a, b) => b.duration - a.duration)
      .slice(0, SLOWEST_COUNT)
    console.log(`\nSlowest ${durations.length} tests:`)
    for (const { name, duration } of durations) {
      console.log(`  ${duration.toFixed(0).padStart(6)} ms  ${name}`)
    }
  }
}
