# LaunchDarkly OpenFeature provider for the Server-Side SDK for Python

[![Quality control checks](https://github.com/launchdarkly/openfeature-python-server/actions/workflows/ci.yml/badge.svg)](https://github.com/launchdarkly/openfeature-python-server/actions/workflows/ci.yml)
[![readthedocs](https://readthedocs.org/projects/launchdarkly-openfeature-python-sdk/badge/)](https://launchdarkly-openfeature-python-sdk.readthedocs.io/en/latest/)

[![PyPI](https://img.shields.io/pypi/v/launchdarkly-openfeature-server.svg?maxAge=2592000)](https://pypi.python.org/pypi/launchdarkly-openfeature-server)
[![PyPI](https://img.shields.io/pypi/pyversions/launchdarkly-openfeature-server.svg)](https://pypi.python.org/pypi/launchdarkly-openfeature-server)

This provider allows for using LaunchDarkly with the OpenFeature SDK for Python.

This provider is designed primarily for use in multi-user systems such as web servers and applications. It follows the server-side LaunchDarkly model for multi-user contexts. It is not intended for use in desktop and embedded systems applications.

> [!WARNING]
> This is a beta version. The API is not stabilized and may introduce breaking changes.

> [!NOTE]
> This OpenFeature provider uses production versions of the LaunchDarkly SDK, which adhere to our standard [versioning policy](https://docs.launchdarkly.com/sdk/concepts/versioning).

# LaunchDarkly overview

[LaunchDarkly](https://www.launchdarkly.com) is a feature management platform that serves trillions of feature flags daily to help teams build better software, faster. [Get started](https://docs.launchdarkly.com/home/getting-started) using LaunchDarkly today!

[![Twitter Follow](https://img.shields.io/twitter/follow/launchdarkly.svg?style=social&label=Follow&maxAge=2592000)](https://twitter.com/intent/follow?screen_name=launchdarkly)

## Supported Python versions

This version of the LaunchDarkly provider works with Python 3.8 and above.

## Getting started

### Requisites

Install the library via pip

```shell
$ pip install launchdarkly-openfeature-server
```

### Usage

```python
from ldclient import Config
from ld_openfeature import LaunchDarklyProvider
from openfeature import api

openfeature_provider = LaunchDarklyProvider(Config("sdk-key"))

api.set_provider(openfeature_provider)

# Refer to OpenFeature documentation for getting a client and performing evaluations.
```

Refer to the [SDK reference guide](https://docs.launchdarkly.com/sdk/server-side/python) for instructions on getting started with using the SDK.

For information on using the OpenFeature client please refer to the [OpenFeature Documentation](https://docs.openfeature.dev/docs/reference/concepts/evaluation-api/).

## OpenFeature Specific Considerations

LaunchDarkly evaluates contexts, and it can either evaluate a single-context, or a multi-context. When using OpenFeature both single and multi-contexts must be encoded into a single `EvaluationContext`. This is accomplished by looking for an attribute named `kind` in the `EvaluationContext`.

There are 4 different scenarios related to the `kind`:
1. There is no `kind` attribute. In this case the provider will treat the context as a single context containing a "user" kind.
2. There is a `kind` attribute, and the value of that attribute is "multi". This will indicate to the provider that the context is a multi-context.
3. There is a `kind` attribute, and the value of that attribute is a string other than "multi". This will indicate to the provider a single context of the kind specified.
4. There is a `kind` attribute, and the attribute is not a string. In this case the value of the attribute will be discarded, and the context will be treated as a "user". An error message will be logged.

The `kind` attribute should be a string containing only contain ASCII letters, numbers, `.`, `_` or `-`.

The OpenFeature specification allows for an optional targeting key, but LaunchDarkly requires a key for evaluation. A targeting key must be specified for each context being evaluated. It may be specified using either `targetingKey`, as it is in the OpenFeature specification, or `key`, which is the typical LaunchDarkly identifier for the targeting key. If a `targetingKey` and a `key` are specified, then the `targetingKey` will take precedence.

There are several other attributes which have special functionality within a single or multi-context.
- A key of `privateAttributes`. Must be an array of string values. [Equivalent to the 'private' builder method in the SDK.](https://launchdarkly-python-sdk.readthedocs.io/en/latest/api-main.html#ldclient.ContextBuilder.private)
- A key of `anonymous`. Must be a boolean value.  [Equivalent to the 'anonymous' builder method in the SDK.](https://launchdarkly-python-sdk.readthedocs.io/en/latest/api-main.html#ldclient.ContextBuilder.anonymous)
- A key of `name`. Must be a string. [Equivalent to the 'name' builder method in the SDK.](https://launchdarkly-python-sdk.readthedocs.io/en/latest/api-main.html#ldclient.ContextBuilder.name)

### Examples

#### A single user context

```python
context = EvaluationContext("the-key")
```

#### A single context of kind "organization"

```python
context = EvaluationContext("org-key", {"kind": "organization"});
```

#### A multi-context containing a "user" and an "organization"

```python
attributes = {
    "kind": "multi",
    "organization": {
        "name": "the-org-name",
        "targetingKey", "my-org-key",
        "myCustomAttribute", "myAttributeValue"
    },
    "user": {
        "key": "my-user-key",
        "anonymous", true
    }
}
context = EvaluationContext(null, attributes)
```

#### Setting private attributes in a single context

```python
attributes = {
    "kind": "organization",
    "myCustomAttribute": "myAttributeValue",
    "privateAttributes": ["myCustomAttribute"]
}

context = EvaluationContext("org-key", attributes)
```

#### Setting private attributes in a multi-context

```python
attributes = {
    "kind": "organization",
    "organization": {
        "name": "the-org-name",
        "targetingKey": "my-org-key",
        # This will ONLY apply to the "organization" attributes.
        "privateAttributes": ["myCustomAttribute"],
        # This attribute will be private.
        "myCustomAttribute": "myAttributeValue",
    },
    "user": [
        "key": "my-user-key",
        "anonymous" = > true,
        # This attribute will not be private.
        "myCustomAttribute": "myAttributeValue",
    ]
}

context = EvaluationContext(null, attributes)
```

## Learn more

Check out our [documentation](http://docs.launchdarkly.com) for in-depth instructions on configuring and using LaunchDarkly. You can also head straight to the [complete reference guide for this SDK](https://docs.launchdarkly.com/sdk/server-side/python).

The authoritative description of all properties and methods is in the [python documentation](https://launchdarkly.github.io/python-server-sdk/).

## Contributing

We encourage pull requests and other contributions from the community. Check out our [contributing guidelines](CONTRIBUTING.md) for instructions on how to contribute to this SDK.

## About LaunchDarkly

* LaunchDarkly is a continuous delivery platform that provides feature flags as a service and allows developers to iterate quickly and safely. We allow you to easily flag your features and manage them from the LaunchDarkly dashboard.  With LaunchDarkly, you can:
    * Roll out a new feature to a subset of your users (like a group of users who opt-in to a beta tester group), gathering feedback and bug reports from real-world use cases.
    * Gradually roll out a feature to an increasing percentage of users, and track the effect that the feature has on key metrics (for instance, how likely is a user to complete a purchase if they have feature A versus feature B?).
    * Turn off a feature that you realize is causing performance problems in production, without needing to re-deploy, or even restart the application with a changed configuration file.
    * Grant access to certain features based on user attributes, like payment plan (eg: users on the ‘gold’ plan get access to more features than users in the ‘silver’ plan). Disable parts of your application to facilitate maintenance, without taking everything offline.
* LaunchDarkly provides feature flag SDKs for a wide variety of languages and technologies. Check out [our documentation](https://docs.launchdarkly.com/sdk) for a complete list.
* Explore LaunchDarkly
    * [launchdarkly.com](https://www.launchdarkly.com/ "LaunchDarkly Main Website") for more information
    * [docs.launchdarkly.com](https://docs.launchdarkly.com/  "LaunchDarkly Documentation") for our documentation and SDK reference guides
    * [apidocs.launchdarkly.com](https://apidocs.launchdarkly.com/  "LaunchDarkly API Documentation") for our API documentation
    * [blog.launchdarkly.com](https://blog.launchdarkly.com/  "LaunchDarkly Blog Documentation") for the latest product updates
