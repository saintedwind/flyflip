/* The browser uses the same two-score update as study.simulate. */
(function (root) {
  'use strict';

  function plan(protocol, seed) {
    const episodes = 2 * protocol.replicates;
    const trials = 2 * protocol.phase_trials;
    const random = new Uint32Array(2 * episodes * trials);
    let state = seed >>> 0;
    // A reproducible browser PRNG. The recorded benchmark uses NumPy's RNG.
    for (let i = 0; i < random.length; i++) {
      state = (state + 0x6D2B79F5) >>> 0;
      let value = Math.imul(state ^ state >>> 15, state | 1);
      value ^= value + Math.imul(value ^ value >>> 7, value | 61);
      random[i] = (value ^ value >>> 14) >>> 0;
    }
    return {episodes, trials, random};
  }

  function simulate(kernel, [a, b], initial, protocol, schedule) {
    const {episodes, trials, random} = schedule;
    const gram = [[kernel[a][a], kernel[a][b]], [kernel[b][a], kernel[b][b]]];
    const scores = [new Float64Array(episodes), new Float64Array(episodes)];
    const accuracy = new Array(trials);
    const sample = [];
    for (let trial = 0; trial < trials; trial++) {
      const flipped = Number(trial >= protocol.phase_trials);
      let hits = 0;
      for (let episode = 0; episode < episodes; episode++) {
        const target = initial ^ Number(episode >= protocol.replicates) ^ flipped;
        const offset = 2 * (trial * episodes + episode);
        const explore = random[offset] / 4294967296 < protocol.exploration;
        const tied = Math.abs(scores[0][episode] - scores[1][episode]) <= 1e-12;
        const choice = explore || tied ? (random[offset + 1] >>> 31) : Number(scores[1][episode] > scores[0][episode]);
        const reward = Number(choice === target);
        const step = protocol.learning_rate * (reward - scores[choice][episode]);
        scores[0][episode] += step * gram[0][choice];
        scores[1][episode] += step * gram[1][choice];
        hits += reward;
        if (episode === 0) sample.push({target, choice, reward});
      }
      accuracy[trial] = hits / episodes;
    }
    return {accuracy, sample};
  }

  function run(data, pair, initial, seed) {
    const {protocol, kernels} = data;
    if (pair.length !== 2 || pair[0] === pair[1] || pair.some(i => !Number.isInteger(i) || i < 0 || i >= kernels.observed.length)) {
      throw new RangeError('Choose two different measured odors');
    }
    if (![0, 1].includes(initial) || !Number.isInteger(seed) || seed < 0 || seed > 0xffffffff) {
      throw new RangeError('Invalid reward order or seed');
    }
    const schedule = plan(protocol, seed);
    const observed = simulate(kernels.observed, pair, initial, protocol, schedule);
    const direct = simulate(kernels.direct, pair, initial, protocol, schedule);
    const controls = kernels.controls.map(kernel => simulate(kernel, pair, initial, protocol, schedule));
    const rewired = controls[0].accuracy.map((_, trial) =>
      controls.reduce((sum, control) => sum + control.accuracy[trial], 0) / controls.length
    );
    return {pair, initial, seed, episodes: schedule.episodes,
      curves: {observed: observed.accuracy, rewired, direct: direct.accuracy},
      tracks: {observed: observed.sample, rewired: controls[0].sample}};
  }

  const api = {plan, simulate, run};
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.FlyFlipModel = api;
}(typeof globalThis === 'object' ? globalThis : this));
