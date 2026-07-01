---
CreatedAt: 2026-06-30T17:40:35Z
LastUpdated: 2026-07-01T03:06:11Z
Type: Note
Status:
tags:
aliases:
---

# C++ Studying

1. unique_ptr vs shared_ptr
	1. Unique ptr is owned, shared_ptr has no ownership/is owned by anyone who has a reference
	2. To avoid cycles creating memory leaks, use weak_ptr alongside shared_ptr
2. std::move
	1. Secretly a cast (&&Original) - converts lvalue to rvalue
3. move ctor/move assignment
	1. Accepts rvalues instead of lvalues
	2. Otherwise equivalent to copy ctor/copy assignment
4. lvalues, rvalues, rvalue refs
	1. lvalues have names/identifiers
	2. rvalues do not, and include expressions (ie '1 + 2' or '2 * r')
5. diamond inheritance
	1. If A inherits from B and C, which both inherit from D, then B and C both have their own unique copies of D
	2. To fix this, they declare their inheritance from D as virtual. This requires A to also provide an initialization list for A despite not directly inheriting from A. This results in one D item used for A as well as both B and C
6. Rule of Three/Five/Zero
	1. Rule of 3: Destructor, copy assignment, copy constructor
	2. Rule of 5: adds move assignment, move constructor
	3. Rule of 0: Use only RAII and you can stick with compiler defaults for the above
7. Virtual Destructors
	1. If a class has any virtual methods, the destructor also needs to be virtual
	2. `virtual ~Class() = 0;` is often seen to make a destructor virtual without providing anything of substance
	3. Virtual destructor is necessary to delete derived class objects through a base class pointer
	4. If the derived class will be used as the derived class (not the base class) then virtual destructor not needed
8. Vtables and Dynamic Dispatch
	1. Every virtual class has a vtable with function pointers to every available function
	2. Every object has a vptr, 8 bytes, pointing to their class's vtable.
	3. A derived class will have any overrides in their list, along side base versions for any method that doesn't provide an override
	4. Virtual function call: object > access vptr > read vtable > method slot > usable function pointer
	5. This overhead means classes should only be declared virtual when needed
