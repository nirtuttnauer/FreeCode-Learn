#!/usr/bin/env python3
"""Author the bundled, dependency-free foundation tracks (original FreeCode exercises)."""
import ast
import copy
import hashlib
import html
import json
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/learning'
ATTENTION = 'https://docs.pytorch.org/tutorials/intermediate/scaled_dot_product_attention_tutorial.html'
SYSTEMS = 'https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/'
LESSONS = []


def lesson(course, module, title, signature, body, cases, concept, task, hint, reflection, *, helpers='', difficulty='Medium'):
    code = helpers.strip() + '\n\nclass Solution:\n    def ' + signature + ':\n' + textwrap.indent(textwrap.dedent(body).strip(), '        ') + '\n'
    namespace = {}
    exec(code, namespace)
    method = getattr(namespace['Solution'](), signature.split('(')[0])
    samples = []
    for args in cases:
        expected = method(*copy.deepcopy(args))
        # No NaNs/infinities may enter the local-test format.
        json.dumps(expected, allow_nan=False)
        names = [a.arg for a in ast.parse(code).body[-1].body[0].args.args][1:]
        samples.append(dict(input=', '.join(f'{name} = {json.dumps(value, ensure_ascii=False)}' for name,value in zip(names,args)), output=json.dumps(expected, ensure_ascii=False), args=args, expected=expected))
    stub = helpers.strip() + '\n\nclass Solution:\n    def ' + signature + ':\n        # ' + task.split('.')[0] + '\n        raise NotImplementedError("Implement this step")\n'
    index = sum(p['course']==course for p in LESSONS)+1
    identifier = -(1000 if course=='llm' else 2000)-index
    statement = f'''<p><strong>Step {index} · {html.escape(module)}</strong></p>
<p>{concept}</p><h3>Build it</h3><p>{task}</p>
<p><strong>Contract:</strong> Implement <code>{html.escape(signature.split('(')[0])}</code> using Python's standard library. Inputs satisfy the constraints stated here. Do not mutate the inputs. Use the provided helpers where present; they represent earlier steps.</p>
<h3>Examples</h3>'''
    for sample in samples[:2]:
        statement += '<pre><strong>Input:</strong> '+html.escape(sample['input'])+'\n<strong>Expected:</strong> '+html.escape(sample['output'])+'</pre>'
    statement += f'''<details><summary>Hint</summary><p>{hint}</p></details>
<h3>Review your understanding</h3><p>{reflection}</p>
<p>Explain your reasoning in Notes before opening the worked solution. Passing the local checks completes this exercise; it does not certify production readiness or evaluate your design explanation.</p>'''
    record=dict(id=identifier,title=title,slug=course+'-'+str(index),url='',difficulty=difficulty,tags=['LLM engineering' if course=='llm' else 'System design',module],premium=False,statement=statement,references={'python':code.lstrip()},starters={'python':stub.lstrip()},samples=samples,sourceURL=ATTENTION if course=='llm' else SYSTEMS,missingImages=[])
    LESSONS.append(dict(course=course,module=module,record=record))


MATH = '''import math

def softmax(values):
    peak = max(values)
    weights = [math.exp(v-peak) for v in values]
    return [w/sum(weights) for w in weights]

def norm(x, eps=1e-5):
    mean = sum(x)/len(x)
    variance = sum((v-mean)**2 for v in x)/len(x)
    return [(v-mean)/math.sqrt(variance+eps) for v in x]

def attend(q, keys, values):
    weights = softmax([sum(a*b for a,b in zip(q,k))/math.sqrt(len(q)) for k in keys])
    return [sum(w*v[j] for w,v in zip(weights,values)) for j in range(len(values[0]))]

def affine(x, weights, bias):
    return [sum(x[i]*weights[i][j] for i in range(len(x)))+bias[j] for j in range(len(bias))]
'''


def build_llm():
    lesson('llm','Represent text','Build a reversible byte tokenizer','tokenize(self, text: str) -> list[int]',
        'return list(text.encode("utf-8"))', [['hello'],['café'],['🤖'],['']],
        'A model consumes token IDs. Start with a tokenizer whose vocabulary is exactly the 256 byte values. UTF-8 makes the mapping reversible across languages; a character may become several bytes. This is a byte baseline, not BPE.',
        'Return the UTF-8 byte values of text as integers from 0 to 255. Empty text produces an empty list.',
        'Python can encode text to bytes; iterating over bytes yields integers.',
        'How would you decode the result? Why do production tokenizers often group bytes into subword tokens?',difficulty='Easy')
    lesson('llm','Represent text','Look up token embeddings','embed(self, tokens: list[int], table: list[list[float]]) -> list[list[float]]',
        'return [list(table[token]) for token in tokens]', [[[0,2,0],[[1,0],[0,1],[0.5,0.5]]],[[],[[1,2]]]],
        'An embedding table has one learned row per token. Looking up IDs produces a sequence-by-width matrix. Repeated IDs share parameter values, but this exercise returns independent row copies.',
        'Return one copied embedding row per token, preserving token order. IDs are valid table indices; all rows have the same width.',
        'Index a row for each ID, then copy it rather than returning an alias.',
        'What are the shapes for a sequence of 128 tokens and an embedding width of 64?',difficulty='Easy')
    lesson('llm','Probabilities and loss','Implement numerically stable softmax','softmax(self, logits: list[float]) -> list[float]',
        'peak=max(logits)\nweights=[math.exp(v-peak) for v in logits]\nreturn [v/sum(weights) for v in weights]', [[[0,0,0]],[[1000,1001,999]],[[-1000,-1000]],[[3.5]]],
        'Softmax turns scores into a probability distribution. Subtracting the largest score leaves the distribution unchanged and prevents exponentials from overflowing.',
        'Return softmax probabilities for a nonempty list of finite logits. Use exp(logit − maximum), then divide by the sum.',
        'Compute the maximum once. Equal logits should produce equal probabilities.',
        'Why does subtracting the same constant from every score leave the normalized result unchanged?',helpers='import math')
    lesson('llm','Probabilities and loss','Measure next-token cross entropy','loss(self, logits: list[list[float]], targets: list[int]) -> float',
        'total=0.0\nfor row,target in zip(logits,targets):\n    peak=max(row)\n    total+=peak+math.log(sum(math.exp(v-peak) for v in row))-row[target]\nreturn total/len(targets)',
        [[[[0,0],[2,0]],[0,0]],[[[1000,1001,999]],[1]],[[[-1000,-1000]],[0]]],
        'For each position, cross entropy is the negative log probability of the correct next token. Use log-sum-exp directly so an extremely small probability does not become log(0).',
        'Return the mean cross entropy in natural-log units over aligned, nonempty logits and valid target IDs. Every row has a common vocabulary size.',
        'For one row use max(row) + log(sum(exp(score−max))) − score[target].',
        'What does a loss of log(vocabulary size) tell you about a uniform model?',helpers='import math')
    lesson('llm','Attention','Implement scaled dot-product attention','attention(self, query: list[float], keys: list[list[float]], values: list[list[float]]) -> list[float]',
        'weights=softmax([sum(a*b for a,b in zip(query,key))/math.sqrt(len(query)) for key in keys])\nreturn [sum(weights[i]*values[i][j] for i in range(len(values))) for j in range(len(values[0]))]',
        [[[1,0],[[1,0],[0,1]],[[10,0],[0,20]]],[[0,0],[[4,2],[1,8]],[[2,4],[6,8]]]],
        'A query scores each key with a dot product divided by the square root of key width. Softmax produces weights for a weighted sum of value vectors. Values may have a different width from keys.',
        'Return the attention output for one query and nonempty keys/values with equal sequence length. Implement the scoring and weighting yourself; the supplied helpers show the earlier mathematics.',
        'A zero query assigns equal weight to every value. Use the key width for the scale.',
        'Which tensor dimension sets the softmax axis? Why scale the dot product?',helpers=MATH.replace('\ndef attend(q, keys, values):\n    weights = softmax([sum(a*b for a,b in zip(q,k))/math.sqrt(len(q)) for k in keys])\n    return [sum(w*v[j] for w,v in zip(weights,values)) for j in range(len(values[0]))]\n',''))
    lesson('llm','Attention','Mask future tokens in causal attention','causal(self, queries: list[list[float]], keys: list[list[float]], values: list[list[float]]) -> list[list[float]]',
        'return [attend(q,keys[:i+1],values[:i+1]) for i,q in enumerate(queries)]',
        [[[[1,0],[0,1]],[[1,0],[0,1]],[[10,0],[0,20]]],[[[1],[2],[3]],[[1],[2],[100]],[[1],[2],[999]]]],
        'Autoregressive decoding must not see future tokens. Query at index i attends only to positions 0 through i, including itself. The first output must not change when future keys or values change.',
        'Return a causal attention output for every query. All three sequences are nonempty and have equal length. Use the provided single-query attention helper.',
        'Slice keys and values to the current position, rather than computing future scores.',
        'Why would unmasked attention make next-token training look better while breaking generation?',helpers=MATH)
    lesson('llm','Attention','Split and combine attention heads','multihead(self, q: list[list[float]], k: list[list[float]], v: list[list[float]], heads: int) -> list[list[float]]',
        'width=len(q[0])//heads\nresult=[]\nfor i,row in enumerate(q):\n    output=[]\n    for h in range(heads):\n        lo,hi=h*width,(h+1)*width\n        output.extend(attend(row[lo:hi],[r[lo:hi] for r in k[:i+1]],[r[lo:hi] for r in v[:i+1]]))\n    result.append(output)\nreturn result',
        [[[[1,0,0,1],[0,1,1,0]],[[1,0,0,1],[0,1,1,0]],[[1,2,3,4],[5,6,7,8]],2],[[[1,2]],[[2,1]],[[3,4]],1]],
        'Multiple attention heads operate on different feature slices, then concatenate their outputs. This exercise begins after Q/K/V projection and ends before the output projection.',
        'Compute causal attention independently for each contiguous feature slice and concatenate in head order. All matrices share a positive width divisible by heads; heads is positive.',
        'The scale for each head uses head width, not the full model width.',
        'Why are learned Q/K/V and output projections still needed around this operation?',helpers=MATH,difficulty='Hard')
    lesson('llm','Transformer block','Normalize each token vector','normalize(self, x: list[float], eps: float) -> list[float]',
        'mean=sum(x)/len(x)\nvariance=sum((v-mean)**2 for v in x)/len(x)\nreturn [(v-mean)/math.sqrt(variance+eps) for v in x]', [[[1,2,3],0.00001],[[5,5],0.00001],[[-2,2],0.00001]],
        'Layer normalization centers and rescales a token’s features. It uses population variance across features. This exercise omits the learned scale and bias.',
        'Return (x − mean) / sqrt(population_variance + eps). x is nonempty and eps is positive.',
        'Divide the squared deviations by the number of features, not n−1.',
        'Why does the constant-vector case require epsilon?',helpers='import math')
    lesson('llm','Transformer block','Build the position-wise feedforward network','feedforward(self, x: list[float], w1: list[list[float]], b1: list[float], w2: list[list[float]], b2: list[float]) -> list[float]',
        'hidden=[max(0,v) for v in affine(x,w1,b1)]\nreturn affine(hidden,w2,b2)',
        [[[1,-1],[[1,0,1],[0,1,-1]],[0,0,0],[[1,0],[0,1],[1,1]],[0,0]],[[0,0],[[1],[1]],[-2],[[3,4]],[1,2]]],
        'The same feedforward weights transform every token independently. A first affine layer expands features, ReLU adds a nonlinearity, and a second layer projects back. Modern models may use other activations.',
        'Compute ReLU(x @ w1 + b1) @ w2 + b2. Matrices have valid compatible shapes; weights use input-by-output orientation.',
        'The affine helper handles the matrix-vector arithmetic. Apply ReLU only between the two projections.',
        'What changes if you remove the nonlinearity?',helpers=MATH)
    lesson('llm','Transformer block','Assemble a pre-norm transformer block','block(self, tokens: list[list[float]]) -> list[list[float]]',
        'normalized=[norm(row) for row in tokens]\nresidual=[]\nfor i,row in enumerate(tokens):\n    attended=attend(normalized[i],normalized[:i+1],normalized[:i+1])\n    residual.append([a+b for a,b in zip(row,attended)])\nreturn [[a+max(0,b) for a,b in zip(row,norm(row))] for row in residual]',
        [[[[1,0],[0,1],[1,1]]],[[[2,-2]]]],
        'A pre-norm block applies normalization before each sublayer and preserves a residual path. This deliberately small block uses identity Q/K/V projections and a same-width ReLU feedforward sublayer.',
        'For each token: u = x + causal_attention(norm(x)); then y = u + ReLU(norm(u)). Q, K, and V are all the normalized token vectors. Return all y vectors. Input is a nonempty matrix of positive width.',
        'Compute every attention output from the original normalized sequence before applying the second residual.',
        'Trace the two residual paths. Which learned projections and parameters would you add to make a full model block?',helpers=MATH,difficulty='Hard')
    lesson('llm','Train and generate','Take one language-model SGD step','train_step(self, logits: list[list[float]], pairs: list[list[int]], rate: float) -> list[list[float]]',
        'gradient=[[0.0]*len(logits[0]) for _ in logits]\nfor previous,target in pairs:\n    probabilities=softmax(logits[previous])\n    for j,p in enumerate(probabilities):\n        gradient[previous][j]+=(p-(1 if j==target else 0))/len(pairs)\nreturn [[v-rate*g for v,g in zip(row,grad)] for row,grad in zip(logits,gradient)]',
        [[[[0,0],[0,0]],[[0,1],[1,0]],0.2],[[[1,0],[0,1]],[[0,1],[0,1]],0.1]],
        'A bigram model learns a next-token distribution conditioned on one previous token. It isolates the language-model loss and optimizer before adding transformer backpropagation. For softmax cross entropy the logit gradient is p − one_hot(target).',
        'Return a new logit table after one full-batch SGD step. Average gradients over all nonempty training pairs, including repeated previous-token rows. Compute all probabilities from the original table, then update once. rate is positive; IDs are valid.',
        'Accumulate a gradient table first. Updating after every pair would implement a different optimizer step.',
        'Why does this train only a bigram model? What extra derivatives and saved activations does transformer training require?',helpers=MATH,difficulty='Hard')
    generation_helpers=MATH+'''
# Fixed untrained, two-feature transformer for inspecting generation mechanics.
EMBEDDINGS = [[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0], [0.0, -1.0]]

def next_logits(ids):
    rows = [[a+b for a,b in zip(EMBEDDINGS[t], [math.sin(i), math.cos(i)])] for i,t in enumerate(ids)]
    normalized = [norm(row) for row in rows]
    h = []
    for i,row in enumerate(rows):
        a = attend(normalized[i], normalized[:i+1], normalized[:i+1])
        u = [x+y for x,y in zip(row,a)]
        h.append([x+max(0,y) for x,y in zip(u,norm(u))])
    last = norm(h[-1])
    return [sum(a*b for a,b in zip(last,e)) for e in EMBEDDINGS]
'''
    lesson('llm','Train and generate','Generate tokens with a tiny transformer','generate(self, prompt: list[int], steps: int) -> list[int]',
        'tokens=list(prompt)\nfor _ in range(steps):\n    logits=next_logits(tokens)\n    tokens.append(max(range(len(logits)),key=lambda i:logits[i]))\nreturn tokens',
        [[[0],4],[[1,2],3],[[3],0]],
        'Autoregressive generation feeds the growing context back through a model. The provided next_logits function combines embeddings, position signals, causal attention, a residual feedforward block, and a vocabulary projection. Its fixed, untrained weights demonstrate mechanics; they do not generate useful language.',
        'Return the prompt plus steps greedy next-token predictions. Use next_logits on the entire current context each step. On a tie choose the smallest token ID. prompt is nonempty with IDs 0–3; steps is 0–10.',
        'Python’s max over an ascending range keeps the first index when scores tie. Copy the prompt before appending.',
        'Which computations repeat for the old tokens? Where would a KV cache help? Explain why a trained model and a real tokenizer are still needed.',helpers=generation_helpers,difficulty='Hard')
    lesson('llm','LLM engineering','Bound an inference KV cache','cache(self, keys: list[list[float]], values: list[list[float]], new_keys: list[list[float]], new_values: list[list[float]], limit: int) -> list',
        'return [[list(row) for row in (keys+new_keys)[-limit:]],[list(row) for row in (values+new_values)[-limit:]]]',
        [[[[1]],[[10]],[[2],[3]],[[20],[30]],2],[[],[],[[1,2]],[[3,4]],4]],
        'A decoding cache stores projected keys and values so previous projections need not be recomputed. Keys and values must stay aligned. A sliding cache also changes the attention context and requires careful position handling in a full model.',
        'Append the new key/value rows, retain only the latest limit positions, and return [keys, values] as copied rows. Old and new key/value counts match; limit is positive.',
        'Concatenate before keeping the final limit elements. Apply exactly the same slice to keys and values.',
        'Estimate KV memory for layers × heads × cached tokens × head width × bytes × two tensors. What changes with grouped-query attention?',difficulty='Easy')
    lesson('llm','LLM engineering','Retrieve context by cosine similarity','retrieve(self, query: list[float], documents: list[list[float]], k: int) -> list[int]',
        'def cosine(vector):\n    denominator=math.sqrt(sum(v*v for v in query)*sum(v*v for v in vector))\n    return sum(a*b for a,b in zip(query,vector))/denominator if denominator else 0.0\nreturn sorted(range(len(documents)),key=lambda i:(-cosine(documents[i]),i))[:k]',
        [[[1,0],[[0,1],[2,0],[1,1]],2],[[0,0],[[1,0],[0,1]],2],[[1,2],[],0]],
        'Retrieval-augmented generation starts by finding relevant context. This exercise isolates exact vector ranking using precomputed embeddings; it does not provide an embedding model or prove answer quality.',
        'Return the indices of the top k document vectors by descending cosine similarity, breaking ties by smaller index. A zero-norm vector has similarity 0. All vectors have query width; 0 ≤ k ≤ document count.',
        'Normalize the dot product by both lengths. Sort using negative similarity and the index.',
        'How would you test retrieval relevance, prevent document leakage, and decide whether generated answers are supported by retrieved evidence?',helpers='import math')
    lesson('llm','LLM engineering','Evaluate masked token perplexity','perplexity(self, losses: list[float], mask: list[int]) -> float',
        'selected=[loss for loss,keep in zip(losses,mask) if keep]\nreturn math.exp(sum(selected)/len(selected))',
        [[[0.6931471805599453,99,0.6931471805599453],[1,0,1]],[[0,1],[1,1]]],
        'Perplexity is exp(mean token negative log likelihood). Padding and ignored prompt positions should not influence the mean. Perplexity comparisons also depend on the tokenizer and evaluation data.',
        'Return exp(mean(losses whose mask is 1)). Equal-length lists contain finite nonnegative natural-log losses; mask contains 0 or 1 and selects at least one loss. Selected mean is below 100.',
        'Average only the included tokens, not the padded sequence length.',
        'Why can lower perplexity fail to imply better task completion or safer answers?',helpers='import math')
    lesson('llm','LLM engineering','Batch requests within a token budget','batch(self, lengths: list[int], budget: int) -> list[list[int]]',
        'batches=[]\ncurrent=[]\nused=0\nfor i,length in enumerate(lengths):\n    if current and used+length>budget:\n        batches.append(current)\n        current=[]\n        used=0\n    current.append(i)\n    used+=length\nif current:batches.append(current)\nreturn batches',
        [[[4,3,5,2],7],[[3,3,3],6],[[],10]],
        'A serving scheduler balances throughput, latency, and memory. Here the budget counts unpadded prompt tokens. Real padded attention, KV memory, output tokens, and continuous batching introduce additional costs.',
        'Partition requests in arrival order into consecutive batches whose sum of lengths is at most budget. Fill each batch until the next request would overflow. Every length is positive and no larger than budget. Return original request indices; empty input returns [].',
        'Flush the current batch before adding a request that would exceed the budget.',
        'How would a very long request affect waiting time? What admission, fairness, and output-token limits would you add?',difficulty='Easy')


def build_systems():
    lesson('systems','Capacity and placement','Estimate required service concurrency','concurrency(self, rps: float, latency_ms: float, utilization: float) -> int',
        'return math.ceil(rps*(latency_ms/1000)/utilization)', [[1000,200,0.5],[50,100,0.8],[0,20,0.7]],
        'Little’s law relates average requests in flight to arrival rate and average latency in a stable system. Add utilization headroom when turning the estimate into a capacity target. This average-based model does not predict tail latency or burst behavior.',
        'Return ceil(requests_per_second × latency_seconds / utilization). rps and latency_ms are nonnegative; utilization is in (0,1].',
        'Convert milliseconds to seconds before multiplying. Round up the final result.',
        'Which assumptions fail during overload? What would p99 latency, queue depth, and burst measurements add?',helpers='import math',difficulty='Easy')
    lesson('systems','Capacity and placement','Place keys on a consistent-hash ring','route(self, nodes: list[int], keys: list[int]) -> list[int]',
        'ring=sorted(nodes)\nreturn [ring[bisect.bisect_left(ring,key)%len(ring)] for key in keys]',
        [[[10,40,90],[0,10,11,90,99]],[[50],[1,99]]],
        'Consistent hashing maps a key to its clockwise successor on a ring. The numeric positions here are already hashed. A real system also needs stable hashing, virtual nodes, replication, and migration planning.',
        'For each key position return the first node position ≥ key, wrapping to the smallest node when necessary. Node positions are distinct, nonempty, and in [0,99]; keys are also in that range.',
        'Sort the nodes, use a lower-bound search, then wrap the resulting index.',
        'Add a node at position 30 to [10,40,90]. Which key interval moves, and why are virtual nodes useful?',helpers='import bisect',difficulty='Easy')
    lesson('systems','Caching and admission','Implement LRU cache eviction','lru(self, capacity: int, operations: list[list]) -> list',
        'cache=OrderedDict()\noutputs=[]\nfor op in operations:\n    if op[0]=="put":\n        cache[op[1]]=op[2]\n        cache.move_to_end(op[1])\n        if len(cache)>capacity:cache.popitem(last=False)\n    else:\n        outputs.append(cache.get(op[1]))\n        if op[1] in cache:cache.move_to_end(op[1])\nreturn outputs',
        [[2,[["put","a",1],["put","b",2],["get","a"],["put","c",3],["get","b"],["get","c"]]],[0,[["put","x",7],["get","x"]]]],
        'An LRU cache evicts the least recently accessed key. Reads and updates refresh recency; misses do not. This local cache has no TTL, concurrency, replication, or persistence.',
        'Simulate put(key,value) and get(key) operations. Return one result per get, using None for misses. capacity is a nonnegative integer; values are integers. Do not mutate operations.',
        'OrderedDict supports moving a key to the newest end and removing the oldest item.',
        'What happens with a hot key, stale values, a cache stampede, or a process restart?',helpers='from collections import OrderedDict')
    lesson('systems','Caching and admission','Enforce a token-bucket limit','allow(self, capacity: float, refill_per_second: float, events: list[list[float]]) -> list[bool]',
        'tokens=capacity\nlast=0.0\naccepted=[]\nfor now,cost in events:\n    tokens=min(capacity,tokens+(now-last)*refill_per_second)\n    ok=tokens>=cost\n    if ok:tokens-=cost\n    accepted.append(ok)\n    last=now\nreturn accepted',
        [[3,1,[[0,2],[0,2],[1,2],[1,1],[5,3]]],[1,0,[[0,1],[10,1]]]],
        'A token bucket permits bursts up to capacity and refills over time. Rejected requests do not consume tokens. A distributed limiter needs an atomic state update and a clock policy.',
        'Start with a full bucket at time 0. For each [time_seconds,cost], refill to at most capacity, then accept only if enough tokens remain. Events are ordered with nondecreasing nonnegative times; capacity and costs are positive, refill is nonnegative.',
        'Advance the refill timestamp for every event, including rejected requests.',
        'How would concurrent workers share this bucket? What should happen when the backing store is unavailable?')
    lesson('systems','Caching and admission','Enforce a sliding-window limit','window(self, times: list[float], duration: float, limit: int) -> list[bool]',
        'accepted=deque()\nresult=[]\nfor now in times:\n    while accepted and accepted[0]<=now-duration:accepted.popleft()\n    ok=len(accepted)<limit\n    if ok:accepted.append(now)\n    result.append(ok)\nreturn result',
        [[[0,0.1,0.2,1,1.1],1,2],[[0,0,0],5,0]],
        'A sliding-window limiter counts accepted requests in (now − duration, now]. The lower boundary is excluded. Recording rejected requests would create a different policy.',
        'Return an allow/deny result per nondecreasing timestamp. Keep at most limit accepted requests within the window. duration is positive; limit is nonnegative.',
        'Expire timestamps at or before now−duration before deciding whether to admit the next request.',
        'Compare token-bucket bursts, fixed-window boundary spikes, and sliding-window storage costs.',helpers='from collections import deque')
    lesson('systems','Reliable writes','Make retries idempotent','idempotency(self, requests: list[list[str]]) -> list',
        'records={}\nresult=[]\nfor key,payload in requests:\n    if key not in records:records[key]=(payload,len(records)+1)\n    stored,identifier=records[key]\n    result.append(identifier if stored==payload else "conflict")\nreturn result',
        [[[["k1","order-a"],["k1","order-a"],["k2","order-b"],["k1","different"]]],[[]]],
        'Retries can arrive after a successful side effect whose response was lost. An idempotency key identifies one logical operation. Reusing the key with a different payload should be rejected, not treated as a valid replay.',
        'Process [key,payload] requests. Allocate sequential IDs starting at 1 for first-seen keys. Replays with the same payload return the original ID; a different payload returns "conflict" without replacing the stored operation.',
        'Store both the original payload and the assigned result for each key.',
        'Where must the deduplication record and side effect be committed atomically? How do expiry and concurrent retries complicate this?')
    lesson('systems','Reliable writes','Check quorum overlap constraints','overlap(self, replicas: int, reads: int, writes: int) -> bool',
        'return 1<=reads<=replicas and 1<=writes<=replicas and reads+writes>replicas and 2*writes>replicas',
        [[3,2,2],[3,1,2],[5,3,3],[3,4,2]],
        'Quorum overlap is a building block: R+W>N ensures every read set overlaps every write set, and 2W>N ensures write sets overlap. These arithmetic constraints alone do not guarantee linearizability or resolve concurrent versions.',
        'Return whether read/write counts are valid positive counts at most replicas and satisfy both overlap inequalities. replicas is positive.',
        'Validate counts first, then check both strict inequalities.',
        'Why can sloppy quorums, conflicting versions, or membership changes invalidate a naive consistency claim?',difficulty='Easy')
    lesson('systems','Reliable writes','Model a queue visibility lease','queue(self, operations: list[list], lease: float) -> list',
        'items=[]\nresult=[]\nfor op in operations:\n    if op[0]=="enqueue":items.append([op[1],float(op[2])])\n    elif op[0]=="ack":items=[item for item in items if item[0]!=op[1]]\n    else:\n        now=op[1]\n        available=next((item for item in items if item[1]<=now),None)\n        result.append(available[0] if available else None)\n        if available:available[1]=now+lease\nreturn result',
        [[[["enqueue","a",0],["enqueue","b",0],["poll",0],["poll",0],["poll",1],["poll",5],["ack","a",5],["poll",5]],5],[[],3]],
        'A visibility lease temporarily hides a polled message. If processing fails and the lease expires, the message becomes eligible again: at-least-once delivery needs idempotent consumers. This simplified queue uses message IDs for acknowledgements; real systems need receipt tokens to reject stale acknowledgements.',
        'Simulate enqueue(id,time), poll(time), and ack(id,time). Return an ID or None for each poll. Pick the earliest enqueued currently visible message, then hide it until poll_time+lease. Ack removes the ID. IDs are unique; operations are time-ordered and lease is positive.',
        'Track a visible-again time for each message and retain original enqueue order.',
        'Why is an ack by ID unsafe when a lease expires and another worker receives the message?',difficulty='Hard')
    lesson('systems','Failure control','Schedule capped backoff with jitter','delays(self, base: float, cap: float, random_fractions: list[float]) -> list[float]',
        'return [min(cap,base*2**i)*fraction for i,fraction in enumerate(random_fractions)]',
        [[1,5,[0.5,0,1,0.25]],[2,2,[0,0.5,1]]],
        'Exponential backoff reduces retry pressure; full jitter spreads retries uniformly between zero and a capped exponential delay. A retry policy also needs deadlines, a retry budget, and rules about which operations are safe to retry.',
        'For attempt i starting at 0, return random_fraction[i] × min(cap, base × 2^i). Fractions are supplied so tests are deterministic; each lies in [0,1]. base and cap are positive and there are at most 20 attempts.',
        'Cap the exponential delay before multiplying by the fraction.',
        'What happens if every layer retries independently? Which non-idempotent operations should never be retried blindly?',difficulty='Easy')
    lesson('systems','Failure control','Implement a circuit-breaker state machine','circuit(self, events: list[list], threshold: int, cooldown: float) -> list[bool]',
        'failures=0\nopen_until=None\nallowed=[]\nfor now,success in events:\n    if open_until is not None and now<open_until:\n        allowed.append(False)\n        continue\n    probe=open_until is not None\n    allowed.append(True)\n    if success:\n        failures=0\n        open_until=None\n    elif probe:\n        open_until=now+cooldown\n    else:\n        failures+=1\n        if failures>=threshold:open_until=now+cooldown\nreturn allowed',
        [[[[0,False],[1,False],[2,True],[6,False],[7,True],[11,True],[12,True]],2,5],[[[0,False],[1,True],[2,False]],1,1]],
        'A circuit breaker stops calling a failing dependency for a cooldown, then permits a recovery probe. Here calls complete synchronously before the next event, so only one probe is in flight. Production concurrency requires an atomic half-open probe permit.',
        'Return whether each [time,success] call is permitted. Closed opens after threshold consecutive failures; a successful call resets that count. Open rejects calls until time ≥ open_until. The first permitted probe closes on success or reopens for another cooldown on failure. Ignore outcomes of rejected events. Times are nondecreasing; threshold and cooldown are positive.',
        'Distinguish an ordinary closed-state failure from a failed half-open probe.',
        'How would multiple processes coordinate the half-open permit? When is a breaker worse than a strict timeout and concurrency limit?',difficulty='Hard')
    lesson('systems','Service design','Implement stable keyset pagination','page(self, rows: list[list[int]], after: list[int], size: int) -> list[list[int]]',
        'return [row for row in sorted(rows) if not after or tuple(row)>tuple(after)][:size]',
        [[[[10,2],[10,1],[11,3],[12,4]],[10,1],2],[[[1,1],[1,2]],[],1],[[[1,1]],[2,2],3]],
        'Keyset pagination uses a stable ordered cursor instead of skipping an offset. A unique tie-breaker prevents equal timestamps from hiding or repeating records. It still needs explicit semantics for inserts, deletes, and snapshots.',
        'Rows are [created_timestamp,unique_id]. Return at most size rows sorted by this pair and strictly after the cursor pair. An empty after means the first page. IDs are unique and size is nonnegative.',
        'Use lexicographic ordering on the complete pair, not only the timestamp.',
        'Which index supports this query? What consistency guarantees can you promise when rows change between page requests?')
    lesson('systems','Service design','Build a URL-shortener service core','shortener(self, requests: list[list[str]]) -> list',
        'alphabet="0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"\nby_url={}\nby_code={}\nresponses=[]\ndef encode(n):\n    out=""\n    while n:\n        out=alphabet[n%62]+out\n        n//=62\n    return out or "0"\nfor method,value in requests:\n    if method=="POST":\n        if value not in by_url:\n            code=encode(len(by_url)+1)\n            by_url[value]=code\n            by_code[code]=value\n        responses.append(by_url[value])\n    else:responses.append(by_code.get(value))\nreturn responses',
        [[[["POST","https://a.example"],["POST","https://b.example"],["POST","https://a.example"],["GET","1"],["GET","missing"]]],[[]]],
        'The service core maps a long URL to a stable short code and resolves codes back to URLs. This exercise fixes an in-memory, single-process contract so you can test behavior before designing the distributed system.',
        'Process POST(url) and GET(code), returning one response per request. First-seen URLs receive base-62 sequential IDs starting at 1 with alphabet 0–9, a–z, A–Z. Repeated URLs reuse their code; unknown codes return None. Valid requests use only POST/GET and nonempty strings.',
        'Maintain forward and reverse maps. Allocate only for a new URL.',
        'Write a design in Notes: estimate traffic and storage; choose ID allocation, schema and indexes; add caching, replication, expiry, abuse controls, observability, and a failure policy. Compare a globally sequential ID with range allocation or random IDs. Local tests assess this core only, not the architecture.',difficulty='Hard')


def diagram(labels):
    width=180*len(labels)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 104">' + '<style>.ground{fill:#ffffff}.node{fill:#e6edf5;stroke:#526575}.label{fill:#172b3a}.edge{stroke:#526575}@media(prefers-color-scheme:dark){.ground{fill:#17232f}.node{fill:#17383c;stroke:#85f1d0}.label{fill:#ecf2f7}.edge{stroke:#a6b7c7}}</style><rect class="ground" width="100%" height="100%"/>']
    for i,label in enumerate(labels):
        x=i*180+12
        parts.append(f'<rect x="{x}" y="22" width="145" height="54" rx="6" class="node"/><text x="{x+72}" y="54" text-anchor="middle" font-family="sans-serif" font-size="14" class="label">{html.escape(label)}</text>')
        if i<len(labels)-1:parts.append(f'<path d="M{x+148} 49h27m-6-5 6 5-6 5" fill="none" class="edge" stroke-width="2"/>')
    blob=(''.join(parts)+'</svg>').encode()
    name=hashlib.sha256(blob).hexdigest()[:24]+'.svg'
    (ROOT/'data/assets'/name).write_bytes(blob)
    return name


def main():
    build_llm();build_systems()
    (OUTPUT/'problems').mkdir(parents=True,exist_ok=True)
    courses=[]
    catalog=[]
    for course,name,summary,labels in [
        ('llm','Transformers & LLM engineering','16 steps: represent text, build attention and a transformer block, then explore training, generation, retrieval, evaluation, and batching. Python basics required; no extra packages.',['Text → IDs','Embeddings','Causal attention','Block → logits','Next token']),
        ('systems','System design','12 steps: estimate capacity, implement core components, exercise failure behavior, then design a service. Local simulations and design-review prompts; no cloud account.',['Requirements','Capacity','Components','Failures','Tradeoffs'])]:
        rows=[entry for entry in LESSONS if entry['course']==course]
        first=rows[0]['record']
        asset=diagram(labels)
        first['statement']='<p><strong>Track map</strong></p><img alt="'+html.escape(' → '.join(labels))+'" src="offline://assets/'+asset+'">'+first['statement']
        groups=[]
        for entry in rows:
            if not groups or groups[-1]['name']!=entry['module']:groups.append(dict(name=entry['module'],questionIDs=[]))
            record=entry['record'];groups[-1]['questionIDs'].append(record['id'])
            (OUTPUT/'problems'/f"{record['id']}.json").write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n')
            catalog.append({k:record[k] for k in ['id','title','slug','difficulty','premium','tags']})
        courses.append(dict(id=course,name=name,summary=summary,groups=groups))
    (OUTPUT/'catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False)+'\n')
    (OUTPUT/'courses.json').write_text(json.dumps(courses,indent=2,ensure_ascii=False)+'\n')
    (OUTPUT/'README.txt').write_text('Original FreeCode learning exercises. Python standard library only.\n\nThese foundation tracks teach concepts through small executable experiments.\nThey do not supply a trained LLM, GPU training environment, distributed deployment,\nor an automatic evaluator for architectural explanations. Notes contain your design reasoning.\n\nThe source links in each lesson are further reading. Lesson text, starter code,\nworked implementations, tests, and diagrams are authored for FreeCode; no third-party tutorial code is copied.\nRebuild bundled content with python3 scripts/build_learning_content.py.\n')
    print(f'Authored {len(courses)} independent learning tracks, {len(catalog)} lessons, {sum(len(e["record"]["samples"]) for e in LESSONS)} local checks.')
    if (ROOT / 'courses/python-engineer/source').exists():
        import subprocess
        import sys
        python = ROOT / '.cache/runtime-bundle/arm64/python/bin/python3'
        subprocess.run([str(python) if python.exists() else sys.executable, '-B', str(ROOT / 'scripts/build_python_engineer.py')], check=True)


if __name__=='__main__':main()
